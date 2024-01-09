import subprocess
import json
import os

#TODO change buildfile if needed to make a fat jar
#NOTE if handlers are needed this is the point to write them
#options: RequestHandler or RequestStreamHandler or no Handler(than method needs to be specified to AWS)

#input path to gradle project
#builds it
def build(project_path):
    #TODO handle potential errors
    command = f"cd {project_path} && .\\gradlew compileJava"
    subprocess.run(command, shell=True)

#create zip - not needed since the fat jar can be deployed 
#values for aws:
    #function_src
    #region
    #functions: list
        #handler
        #function_name
        #memory - TODO estimate it this should already be implemented with testops

#TODO extend for gcp
def write_tfvars(values: dict):
    tfvars_path = ".\\terraform\\terraform.tfvars.json"
    #try reading existing vars
    with open(tfvars_path, "r") as tfvars_file:
            tfvars = json.load(tfvars_file)

    #TODO should not be all values, when more providers are added
    amazon_values = values

    tfvars["amazon"].update(amazon_values)
    
    with open(tfvars_path, "w") as tfvars_file:
        json.dump(tfvars, tfvars_file, indent=4)

write_tfvars({"region":"I changed the region"})
# write_tfvars({"region":"us-east-1", "function_src": "Baas is great", "functions": [{"handler": "org.example.baas.AWSRequestHandler", "function_name": "handleRequest", "memory": 256, "timeout": 3}]})

def helloworld():
    print('greetings from Baas')

