import subprocess
import json
from python_terraform import Terraform

terraform_dir = ".\\terraform"
#TODO change buildfile if needed to make a fat jar
#NOTE if handlers are needed this is the point to write them
#options: RequestHandler or RequestStreamHandler or no Handler(than method needs to be specified to AWS)

#input path to gradle project
#builds it
def build(project_path):
    #TODO handle potential errors
    command = f"cd {project_path} && .\\gradlew build"
    print(command)
    output = subprocess.run(command, shell=True, capture_output=True)
    print(output.stdout.decode('utf-8'))
    print(output.stderr.decode('utf-8'))

#create zip - not needed since the fat jar can be deployed 
#values for aws:
    #function_src
    #region
    #functions: list
        #handler
        #function_name
        #memory - TODO estimate it this should already be implemented with testops

#TODO make it work not only for updates but also if file does not exist yet
#TODO extend for gcp
def write_tfvars(values: dict):
    tfvars_path = f"{terraform_dir}\\terraform.tfvars.json"
    #try reading existing vars
    with open(tfvars_path, "r") as tfvars_file:
            tfvars = json.load(tfvars_file)

    #TODO should not be all values, when more providers are added
    amazon_values = values

    tfvars["amazon"].update(amazon_values)
    
    with open(tfvars_path, "w") as tfvars_file:
        json.dump(tfvars, tfvars_file, indent=4)

#run terraform file
#not sure if this method makes sense - instead of calling this method the Terraform should probably be called directly
#but then the main file will have to call it
#NOTE capture_output=True returns a tuple: (ret_code, out, err)
def terraform(command: str):
    terraform = Terraform(working_dir=terraform_dir)
    terraform.init()

    if command =='plan':
         output:tuple = terraform.plan(capture_output=True)

    if command =='apply':
         output:tuple = terraform.apply(capture_output=True, skip_plan=True)

    if command =='destroy':
         output:tuple = terraform.apply(capture_output=True, skip_plan=True)
    print(output[1])
    print(output[2])

    # tf.apply(skip_plan=True) 

###############################
#commands

# write_tfvars({"region":"I changed the region"})
write_tfvars({"region":"us-east-1", "function_src": "C:\\Users\\Johann\\Documents\\uibk\\BachelorArbeit\\testOpsGradleImpl\\build\\libs\\testOpsGradleImpl-1.0-SNAPSHOT.jar", "functions": [{"handler": "org.example.baas.AWSRequestHandler", "function_name": "handleRequest", "memory": 256, "timeout": 3}]})

# terraform('apply')
# cd C:\Users\Johann\Documents\uibk\BachelorArbeit\testOpsGradleImpl && .\gradlew build
# project_path = 'C:\\Users\\Johann\\Documents\\uibk\\BachelorArbeit\\testOpsGradleImpl'
# build(project_path)