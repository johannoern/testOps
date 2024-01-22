import json
import os
import re
from Baas import helpers
from Baas import aws_deploy_helpers as aws_helpers
from python_terraform import Terraform

#LATER possible it is nicer to use logging instead of print ...
#this file deploys your function using terrafrom
#prerequisite terraform

terraform_default_dir = ".\\terraform"
default_region = "us-east-1"

#project_path, main_class/aws_handler, function_name
def build(project_path, main_class, function_name):
    aws_handler, function_name = aws_helpers.implement_handler(main_class, function_name)

#LATER it is possible to add a flag to skip the adaption
#for example if shadow is used to make a fat jar the build file would be adapted without need
    aws_helpers.adapt_build_file(project_path, aws_handler)

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
    aws_function_src = get_function_src(aws_code, tfvars)
    
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
        print("terraform plan")
        helpers.execute(f"cd {terraform_dir} && terraform plan")
        return

    if command =='apply':
        print("terraform apply")
        helpers.execute(f"cd {terraform_dir} && terraform apply")
        output = tf.output(capture_output = True)
        return output["lambda_arns"]["value"]

    if command =='destroy':
        print("terraform destroy")
        helpers.execute(f"cd {terraform_dir} && terraform destroy")
        return

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

"""helpers for aws-tfvars"""
def get_function_src(aws_code, tfvars):
    if not aws_code == None:
        return aws_code
    else:
        print("no aws_code passed. Trying to find it in the terrform variables")
        try:
            aws_function_src = tfvars["amazon"]["function_src"]
        except KeyError as e:
            raise ValueError("KeyError: Key 'aws_code' is required but not found.\n after testops build 'aws_code' is set automatically") from e
        return aws_function_src

def write_tfvars(tfvars_path, tfvars, tfvars_update):
    if not "amazon" in tfvars:
        tfvars["amazon"] = tfvars_update
    else:
        tfvars["amazon"].update(tfvars_update)
    
    with open(tfvars_path, "w") as tfvars_file:
        json.dump(tfvars, tfvars_file, indent=4)

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