import json
import re
from subprocess import CalledProcessError
import toml
import shutil
from Baas import helpers
import os
from git import Repo

#this file helps finding the optimal memory for your function using:
#Powertuner - https://github.com/alexcasalboni/aws-lambda-power-tuning/
#prerequisites
    #1. sam cli - https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
    #2. docker - https://docs.docker.com/engine/install/
    #3. git bash - https://www.git-scm.com/downloads

def get_power_tuning_path():
    return os.path.join('.', 'Baas', 'aws-lambda-power-tuning')

#worked 15.01. 1:10
def powertuner_setup():
    powertuner_url="https://github.com/alexcasalboni/aws-lambda-power-tuning.git"
    if not os.path.isdir(get_power_tuning_path()):
        Repo.clone_from(powertuner_url, get_power_tuning_path())
    #build sam app
    #NOTE check the linkage of the command - probably does not work in all editors
    #also would be great if output was continous to know that progress is being made
    command = f"cd {get_power_tuning_path()} && sam build"

    helpers.execute(command)

#worked 15.01. 01:26
#creates default config (samconfig.toml) file overwriting defaults if param is given in configs
#!!!name must be given
def create_config_file(configs:dict):
    wanted_keys = ['name', 'version', 'stack_name', 'resolve_s3', 's3_prefix', 'region', 'confirm_changeset', 'capabilities', 'parameter_overrides', 'image_repositories'] # The keys you want
    configs = dict((k, configs[k]) for k in wanted_keys if k in configs)  
    power_tuning_path = get_power_tuning_path()
    
    #copy default file if no file exists in aws-lambda-power-tuning
    toml_path = os.path.join(power_tuning_path, 'samconfig.toml')
    if not os.path.exists(toml_path):
        default_path = os.path.join('.','Baas', 'samconfig.toml')
        shutil.copy(default_path, power_tuning_path)    

    if not configs.keys() >= {"stack_name", "s3_prefix"}:
        if "name" in configs.keys():
            configs.update({"stack_name":configs["name"]})
            configs.update({"s3_prefix":configs["name"]})
        else:
            raise Exception("the 'name' attribute has to be provided - alternatively 'stack_name' and and 's3_prefix' can be provided separately")
        
    #validate stack_name
    if not re.match("[a-zA-Z][-a-zA-Z0-9]*", configs["stack_name"]):
        print (f"{configs['stack_name']}failed to satisfy constraing: Stack_name/Name must satisfy regular expression pattern: [a-zA-Z][-a-zA-Z0-9]*")
   
    #open the default config and update it with the input configs
    with open(toml_path, 'r') as file:
        samconfig = toml.load(file)
    samconfig['default']['deploy']['parameters'].update(configs)
    with open(toml_path, "w") as toml_file:
        toml.dump(samconfig, toml_file)
    return configs

#build state machine
def build_statemachine():
    #go to the aws_lambda_power_tuning folder
    command = f"cd {get_power_tuning_path()} && sam deploy"
    try:
        helpers.execute(command)
    except CalledProcessError as e:
        print(e)
        print("testops ignores error and carries on with existing Stack")
        

#fill json for execution
    #NOTE could be extended to payload, parallelInvocation - may mem configs can be set for the user
    #AWS_regions/region, lambdaARN, strategy - payload, parallelInvocation
#worked 15.01. 19:18
def fill_json(lambdaARN, memory_configs = [128, 256], strategy="cost"):
    #read sample json
    sample_input_file = os.path.join("Baas", "sample-execution-input.json")
    with open(sample_input_file, "r") as input_file:
            input = json.load(input_file)

    #updating rest #lambdaARN, memory_configs, strategy
    update_dict = {"lambdaARN":lambdaARN, "powerValues":memory_configs, "strategy":strategy}
    input.update(update_dict)

    output_path = os.path.join(get_power_tuning_path(), "Scripts", "execution_input.json")

    with open(output_path, "w") as input_file:
        json.dump(input, input_file, indent=4)

def execute_power_tuning(function_name, stack_name):
    script_path = os.path.join(get_power_tuning_path(), 'scripts')
    command = f"cd {script_path} && .\execute.sh {stack_name} {function_name}_analysis.json"
    helpers.execute(command)
    
