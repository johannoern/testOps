import json
import logging
import os
import pystache
import re
from Baas import helpers
from python_terraform import Terraform

#this file deploys your function using terrafrom
#prerequisite terraform

terraform_default_dir = ".\\terraform"
default_region = "us-east-1"

#project_path, main_class/aws_handler, function_name
def build(project_path, main_class, function_name):
    aws_handler, function_name = implement_handler(main_class, function_name)

#LATER it is possible to add a flag to skip the adaption
#for example if shadow is used to make a fat jar the build file would be adapted without need
    adapt_build_file(project_path, aws_handler)

    command = f"cd {project_path} && .\\gradlew build"
    helpers.execute(command)

#LATER catch potential errors, also check how gradle builds are named
    version = read_gradle_version(os.path.join(project_path, "build.gradle"))
    jar_name = os.path.basename(project_path) + "-" + version + ".jar"
    jar_path = os.path.join(project_path, "build", "libs", jar_name).replace("\\","/")
    return {"aws_code": jar_path, "aws_handler": aws_handler, "function_name": function_name}

#LATER this should all work for more than one function at a time - changes in the json necessary
#NOTE memory could may be be estimated somehow
#NOTE maybe old analyzer could be removed - makes args more and function more readable and I do not think is needed anyways
def prepare_tfvars(aws_handler, function_name, terraform_dir=terraform_default_dir, aws_code=None, region='us-east-1', old_analyzer=False, configs = None):   
    #terraform_dir
    tfvars = get_tfvars(terraform_dir)  
    #aws_code
    aws_function_src = get_aws_function_src(aws_code, tfvars)
    
    if old_analyzer:
        for mem_config in configs["AWS_regions"][region]["memory_configurations"]:
            functions.append({"handler":aws_handler, "function_name":f"{function_name}_{mem_config}MB", "memory":mem_config, "timeout": 3})
    
    memory = 256

    functions = []
    functions.append({"handler":aws_handler, "function_name":function_name, "memory":memory, "timeout": 3})
    
    tfvars_update = {"region":region, "function_src":aws_function_src, "functions":functions}

    write_tfvars(f"{terraform_dir}\\terraform.tfvars.json", tfvars, tfvars_update)

#run terraform file
#NOTE would be nicer with terraform_python    
def terraform(command: str, terraform_dir):
    tf = Terraform(working_dir=terraform_dir)
    helpers.execute(f"cd {terraform_dir} && terraform init")

    if command =='plan':
        logging.info("terraform plan")
        helpers.execute(f"cd {terraform_dir} && terraform plan")
        return

    if command =='apply':
        logging.info("terraform apply")
        helpers.execute(f"cd {terraform_dir} && terraform apply")
        output = tf.output(capture_output = True)
        return output["lambda_arns"]["value"]

    if command =='destroy':
        logging.info("terraform destroy")
        helpers.execute(f"cd {terraform_dir} && terraform destroy")
        return

"""extra for writing tfvars"""
def get_aws_function_src(aws_code, tfvars):
    if not aws_code == None:
        return aws_code
    else:
        logging.info("no aws_code passed. Trying to find it in the terrform variables")
        try:
            aws_function_src = tfvars["amazon"]["function_src"]
        except KeyError as e:
            raise ValueError("KeyError: Key 'aws_code' is required but not found.\n after testops build 'aws_code' is set automatically") from e
        return aws_function_src

def write_tfvars(tfvars_path, tfvars, tfvars_update):
    if not "amazon" in tfvars:
        tfvars["amazon"] = tfvars_update
        logging.info("amazon terraform variables created")
    else:
        tfvars["amazon"].update(tfvars_update)
        logging.info("amazon terraform variables updated")
    
    with open(tfvars_path, "w") as tfvars_file:
        json.dump(tfvars, tfvars_file, indent=4)

def get_tfvars(terraform_dir):
    tfvars_path = f"{terraform_dir}\\terraform.tfvars.json"
    try:
        with open(tfvars_path, 'r') as tfvars_file:
            tfvars = json.load(tfvars_file)
    except FileNotFoundError:
        tfvars = {}
        with open(tfvars_path, 'w') as tfvars_file:
            tfvars_file.write("{}")
    return tfvars

"""all the extra functions für aws"""
#NOTE if main hash has changed or does not exist handler has to be rewritten
#TODO also if the Handler needed to change as the main_function changes that also has to return false - may be store the hash of the orig main
def handler_implemented(main_class):
    if "RequestHandler" in main_class:
        return True
    with open(main_class, "r") as main:
        content = main.read()
        match = re.search(r"implements(\s+(Request[^ ]*[^>]*>)|\sRequestStreamHandler)", content)
    if match:
        return True
    else:
        return False

#LATER cannot build RequestStreamHandler only RequestHandler
def implement_handler(main_class, function_name):
    if handler_implemented(main_class):
        logging.info("handler is already implemented")
        return main_class, function_name
    
    logging.info("implementing handler")
    package, output_type, inputs = parse_main(main_class, function_name)

    main_class_name = os.path.basename(main_class)
    main_folder = os.path.dirname(main_class)

    if main_class_name.endswith(".java"):
        main_class_name = main_class_name[:-5]

    if not inputs == "":
        inputs = "input"

    if output_type == "void":
        methodcall = f"{main_class_name}.{function_name}({inputs})"
        output_type = "Object"
    else:
        methodcall = f"output = {main_class_name}.{function_name}({inputs})"

    #NOTE input types should ideally not be Object
    #unpacking object has to be done by the function - would be nicer if the code did that for you
    context = {"package":package, "input_type": "Object", "output_type": output_type, "method_call": methodcall}
    with open(os.path.join('.', 'Baas', 'request_handler.mustache'), "r") as template_file:
        template = template_file.read()
    
    handler_content = pystache.render(template, context)

    aws_handler = os.path.join(main_folder, "AWSRequestHandler.java")
    with open(aws_handler, "w") as handler:
        handler.write(handler_content)
    aws_handler = package + ".AWSRequestHandler"
    aws_function_name = "handleRequest"
    return aws_handler, aws_function_name

#LATER probably google and azure will need their own adaptions
def adaptation_needed(project_path):
    build_file = os.path.join(project_path, 'build.gradle')
    with open(build_file, 'r') as file:
        content = file.read()
        if 'jar {' in content or 'jar{' in content:
            return False
        else:
            return True

def adapt_build_file(project_path, aws_handler):
    add_lambda(project_path)
    if not adaptation_needed(project_path):
        logging.info(f"buildfile () does not need changes")
        return
    build_file = os.path.join(project_path, 'build.gradle')
    fat_jar = os.path.join('.', 'Baas', 'fat_jar.mustache')
    with open(fat_jar, 'r') as add:
        template = add.read()
        content =  pystache.render(template, {"main_class":aws_handler})       
        with open(build_file, 'a') as build_file:
            build_file.write(content)

def add_lambda(project_path):
    build_file = os.path.join(project_path, 'build.gradle')

    with open(build_file, 'r') as file:
        build_gradle_content = file.read()

    # Define the dependency string to be added
    dependency_string = "implementation 'com.amazonaws:aws-lambda-java-core:1.2.3'"

    # Check if the dependency already exists in the build.gradle file
    if dependency_string not in build_gradle_content:
        logging.info("adding 'com.amazonaws:aws-lambda-java-core:1.2.3' dependency to build.gradle")
        dependencies_index = build_gradle_content.find('dependencies {') + len('dependencies {')
        modified_build_gradle_content = (
            build_gradle_content[:dependencies_index] +
            f"\n    {dependency_string}\n" +
            build_gradle_content[dependencies_index:]
        )

        # Write the modified content back to the build.gradle file
        with open(build_file, 'w') as file:
            file.write(modified_build_gradle_content)
    else:
        logging.info("'com.amazonaws:aws-lambda-java-core:1.2.3' dependency already in build.gradle")

def parse_main(main_class, function_name):
    with open(main_class, "r") as main_class:
        content = main_class.read()
        package = re.search(r"\s*package\s*([^;\s]*)", content).group(1)
        #finds the input attributes and the out put type https://regex101.com/r/OezR0I/1
        pattern = rf" ([^\s]*) {function_name}.*\(([^\)]*)\)"
        function_match = re.search(pattern, content)
        output_type = function_match.group(1)
        inputs = function_match.group(2)
        return package, output_type, inputs

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
 