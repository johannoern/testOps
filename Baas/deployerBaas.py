import datetime
import json
import os
import re
import zipfile
from Baas import helpers
from Baas import aws_deploy_helpers as aws_helpers
from python_terraform import Terraform

#LATER possible it is nicer to use logging instead of print ...
#this file deploys your function using terrafrom
#prerequisite terraform

terraform_default_dir = ".\\terraform"
default_region = "us-east-1"

#project_path, main_class/aws_handler, function_name
def build(project_path, main_class, function_name, provider):
    aws_handler, aws_function_name, gcp_function_name = aws_helpers.implement_handler(main_class, function_name, provider)

#LATER it is possible to add a flag to skip the adaption
#for example if shadow is used to make a fat jar the build file would be adapted without need
    aws_helpers.adapt_build_file(project_path, aws_handler)

    command = f"cd {project_path} && .\\gradlew build"
    helpers.execute(command)

#LATER catch potential errors, also check how gradle builds are named
    version = read_gradle_version(os.path.join(project_path, "build.gradle"))
    jar_name = os.path.basename(project_path) + "-" + version + ".jar"
    libs_path = os.path.join(project_path, "build", "libs")
    jar_path = os.path.join(libs_path, jar_name).replace("\\","/")
    

    formatted_datetime = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    src_name = "output_"+formatted_datetime
    zip_path = os.path.join(libs_path, src_name + ".zip").replace("\\","/")
    #delete all output*.zip files
    
    # Iterate through the files
    for file_name in os.listdir(libs_path):
        # Check if the string_to_match is present in the filename
        if "output_" in file_name:
            # Construct the full path to the file
            file_path = os.path.join(libs_path, file_name)
            os.remove(file_path)
    
    
    with zipfile.ZipFile(zip_path, 'w') as zip_file:
        print(jar_path)
        zip_file.write(jar_path, arcname=os.path.basename(jar_path))
    return {"aws_code": jar_path, "gcp_code":zip_path, "aws_handler": aws_handler, "gcp_handler": aws_handler, "aws_function_name": aws_function_name, "gcp_function_name": gcp_function_name}

#LATER this should all work for more than one function at a time - changes in the json necessary
#NOTE may be variables should be overwritten rather than updated
#NOTE memory could may be be estimated somehow
#NOTE maybe old analyser could be removed - makes args more and function more readable and I do not think is needed anyways
def prepare_tfvars_aws(aws_handler, aws_function_name, terraform_dir=terraform_default_dir, aws_code=None, old_analyser=False, mem_configs = None, region='us-east-1'):   
    print("preparing_tfvars_aws")
    #terraform_dir
    tfvars = get_tfvars(terraform_dir)  
    #aws_code
    aws_function_src = get_function_src(aws_code, tfvars)

    functions = []

    if old_analyser:
        for mem_config in mem_configs:
            functions.append({"handler":aws_handler, "function_name":f"{aws_function_name}_{mem_config}MB", "memory":mem_config, "timeout": 3})
    
    memory = 256


    functions.append({"handler":aws_handler, "function_name":aws_function_name, "memory":memory, "timeout": 3})
    
    tfvars_update = {"region":region, "function_src":aws_function_src, "functions":functions}

    amazon = {"amazon":tfvars_update}
    tfvars.update(amazon)

    write_tfvars(f"{terraform_dir}\\terraform.tfvars.json", tfvars)

def prepare_tfvars_gcp(gcp_handler, gcp_function_name, gcp_project, terraform_dir=terraform_default_dir, gcp_code=None, old_analyser=False, mem_configs=None, region="us-central1"):
    print("preparing_tfvars_gcp")
    #terraform_dir
    tfvars = get_tfvars(terraform_dir)  
    #aws_code
    gcp_function_src = get_function_src(gcp_code, tfvars)

    functions = []

    if old_analyser:
        for mem_config in mem_configs:
            functions.append({"handler":gcp_handler, "function_name":f"{gcp_function_name}_{mem_config}MB", "memory":mem_config, "timeout": 3})
    
    memory = 256

    functions.append({"handler":gcp_handler, "function_name":gcp_function_name, "memory":memory, "timeout": 3})
    
    tfvars_update = {"region":region, "function_src":gcp_function_src, "project":gcp_project, "src_name":os.path.basename(gcp_code), "functions":functions}

    gcp = {"gcp":tfvars_update}
    tfvars.update(gcp)

    write_tfvars(f"{terraform_dir}\\terraform.tfvars.json", tfvars)

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

def write_tfvars(tfvars_path, tfvars):    
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