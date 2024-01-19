import json
import os
import pystache
import re
import sys
from Baas import helpers
from python_terraform import Terraform

#TODO use handler instead of main_class

terraform_default_dir = ".\\terraform"
def handler_implemented(main_class):
    with open(main_class, "r") as main:
        content = main.read()
        match = re.search(r"implements(\s+(Request[^ ]*[^>]*>)|\sRequestStreamHandler)", content)
    if match:
        return True
    else:
        return False

#LATER cannot build RequestStreamHandler only RequestHandler
#do before build and change main_class
def implement_handler(configs:dict):
    with open(os.path.join('.', 'Baas', 'request_handler.mustache'), "r") as template_file:
        template = template_file.read()

    with open(configs["main_class"], "r") as main_class:
        content = main_class.read()
        package_match = re.search("\s*package\s*([^;\s]*)", content)
        package = package_match.group(1)
        #https://regex101.com/r/OezR0I/1
        pattern = f" ([^\s]*) {configs['function_name']}.*\(([^\)]*)\)"
        function_match = re.search(pattern, content)
        output_type = function_match.group(1)
        inputs = function_match.group(2)
    #LATER think about backslashes
        
    main_folder = configs["main_class"].split("/")
    main_class_name = main_folder.pop()
    if main_class_name.endswith(".java"):
        main_class_name = main_class_name[:-5]  
   
    main_folder = "/".join(main_folder)
    
    #NOTE input types should ideally not be Object
    #NOTE unpacking object has to be done by the function - would be nicer if the code did that for you
    if not inputs == "":
        inputs = "input"

    if output_type == "void":
        methodcall = f"{main_class_name}.{configs['function_name']}({inputs})"
        output_type = "Object"
    else:
        methodcall = f"output = {main_class_name}.{configs['function_name']}({inputs})"

    context = {"package":package, "input_type": "Object", "output_type": output_type, "method_call": methodcall}
    handler_content = pystache.render(template, context)

    main_class_path = os.path.join(main_folder, "AWSRequestHandler.java").replace("\\","/")
    with open(main_class_path, "w") as handler:
        handler.write(handler_content)
        
    configs["main_class"] = main_class_path
    configs["aws_handler"] = main_class_path
    return configs

#implementation 'com.amazonaws:aws-lambda-java-core:1.2.3'
def adapt_build_file(project_path, main_class):
    build_file = os.path.join(project_path, 'build.gradle')
    fat_jar = os.path.join('.', 'Baas', 'fat_jar.mustache')
    with open(fat_jar, 'r') as add:
        template = add.read()
        content =  pystache.render(template, {"main_class":main_class})       
        with open(build_file, 'a') as build_file:
            build_file.write(content)

def adaptation_needed(project_path):
    build_file = os.path.join(project_path, 'build.gradle')
    with open(build_file, 'r') as file:
        content = file.read()
        if 'jar {' in content or 'jar{' in content:
            return False
        else:
            return True

def add_lambda(project_path):
    build_file = os.path.join(project_path, 'build.gradle')

    with open(build_file, 'r') as file:
        build_gradle_content = file.read()

    # Define the dependency string to be added
    dependency_string = "    implementation 'com.amazonaws:aws-lambda-java-core:1.2.3'"

    # Check if the dependency already exists in the build.gradle file
    if dependency_string not in build_gradle_content:
        # Add the dependency to the dependencies block
        dependencies_index = build_gradle_content.find('dependencies {') + len('dependencies {')
        modified_build_gradle_content = (
            build_gradle_content[:dependencies_index] +
            f"\n    {dependency_string}\n" +
            build_gradle_content[dependencies_index:]
        )

        # Write the modified content back to the build.gradle file
        with open(build_file, 'w') as file:
            file.write(modified_build_gradle_content)

def read_gradle_version(gradle_file_path):
    with open(gradle_file_path, 'r') as file:
        content = file.read()

    # Use a regular expression to find the version pattern in the file content
    version_match = re.search(r"version[\s=]+['\"]([^'\"]+)['\"]", content)

    if version_match:
        version = version_match.group(1)
        return version
    else:
        raise ValueError("Version not found in the Gradle file")
    
#input path to gradle project
#builds it
def build(configs:dict):
    project_path = configs["project_path"]
    if not handler_implemented(configs["main_class"]):
        configs = implement_handler(configs)

    if configs.get("adaption", True):
        if adaptation_needed(project_path):
            adapt_build_file(project_path, configs["main_class"])
    
    add_lambda(project_path)

    command = f"cd {project_path} && .\\gradlew build"
    helpers.execute(command)

#LATER catch potential errors, also check how gradle builds are named
    if not "aws_code" in configs:
        version = read_gradle_version(os.path.join(project_path, "build.gradle"))
        jar_name = os.path.basename(project_path) + "-" + version + ".jar"
        jar_path = os.path.join(project_path, "build", "libs", jar_name).replace("\\","/")
        configs.update({"aws_code": jar_path})
    return configs
    
#values for aws:
    #function_src
    #region
    #functions: list
        #handler
        #function_name
        #memory

#LATER extend for gcp
def write_tfvars(configs: dict):
    terraform_dir = configs.get("terraform_dir", terraform_default_dir)
    tfvars_path = f"{terraform_dir}\\terraform.tfvars.json"
    try:
        with open(tfvars_path, 'r') as tfvars_file:
            tfvars = json.load(tfvars_file)
    except FileNotFoundError:
        tfvars = {}
        with open(tfvars_path, 'w') as tfvars_file:
            tfvars_file.write("{}")        
        
    #fallback to default region (us-east-1) if no region is found
    default_region = 'us-east-1'
    region = next(iter(configs.get("AWS_regions", default_region)), default_region)

    try:
        aws_function_src = configs["aws_code"]

    #if function src neither already in tfvars nor in the configs nothing can be deployed 
    except KeyError:
        try:
            aws_function_src = tfvars["amazon"]["function_src"]
        except KeyError as e:
            raise ValueError("KeyError: Key 'aws_code' is required but not found.\n after testops build 'aws_code' is set automatically") from e

    #LATER this should all work for more than one function at a time - changes in the json necessary
    #needed if you want to use the old analyser
    if configs.get('old_analyzer', False):
        for mem_config in configs["AWS_regions"][region]["memory_configurations"]:
            functions.append({"handler":configs["aws_handler"], "function_name":f"{configs['function_name']}_{mem_config}MB", "memory":mem_config, "timeout": 3})

    #NOTE memory could may be be estimated somehow
    memory = 256

    functions = []
    functions.append({"handler":configs["aws_handler"], "function_name":configs['function_name'], "memory":memory, "timeout": 3})
    
    if not "amazon" in tfvars:
        tfvars["amazon"] = {"region":region, "function_src":aws_function_src, "functions":functions}
    else:
        tfvars["amazon"].update({"region":region, "function_src":aws_function_src, "functions":functions})
    
    with open(tfvars_path, "w") as tfvars_file:
        json.dump(tfvars, tfvars_file, indent=4)

#run terraform file
#NOTE would be nicer with terraform_python
    
def terraform(command: str, terraform_dir):
    helpers.execute(f"cd {terraform_dir} && terraform init")

    if command =='plan':
        print("terraform plan")
        helpers.execute(f"cd {terraform_dir} && terraform plan")
        return

    if command =='apply':
        print("terraform apply")
        helpers.execute(f"cd {terraform_dir} && terraform apply")
        output = terraform.output(capture_output = True)
        return output["lambda_arns"]["value"]

    if command =='destroy':
        print("terraform destroy")
        helpers.execute(f"cd {terraform_dir} && terraform destroy")
        return