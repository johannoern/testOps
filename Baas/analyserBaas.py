import json
import toml
import shutil
import subprocess
import os
import sys
from git import Repo

#this file helps finding the optimal memory for your function using:
#Powertuner - https://github.com/alexcasalboni/aws-lambda-power-tuning/
#prerequisites
    #1. sam cli - https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
    #2. docker - https://docs.docker.com/engine/install/
#NOTE I am not quite sure about the git link
    #3. git bash - https://www.git-scm.com/downloads

#TODO get rid of the shell=True and make it work independent of the platform

def get_power_tuning_path():
    return os.path.join('.', 'Baas', 'aws-lambda-power-tuning')

#NOTE maybe only call and have check=True
#TODO shell True probably does not work across platforms
def execute(command:str):
    subprocess.check_call(command, shell=True, stdout=sys.stdout, stderr=subprocess.STDOUT)

#worked 15.01. 1:10
def powertuner_setup():
    powertuner_url="https://github.com/alexcasalboni/aws-lambda-power-tuning.git"
    if not os.path.isdir(get_power_tuning_path()):
        Repo.clone_from(powertuner_url, get_power_tuning_path())
    #build sam app
    #TODO check the linkage of the command - probably does not work in all editors
    #also would be great if output was continous to know that progress is being made
    command = f"cd {get_power_tuning_path()} && sam build"


    output = subprocess.run(command, shell=True, capture_output=True, text=True)
    print("this is the stdout: " + output.stdout)
    print("this is the stderr: " + output.stderr)

#worked 15.01. 01:26
#creates default config file overwriting defaults if param is given in configs
#!!!name must be given
def create_config_file(configs:dict):
    power_tuning_path = get_power_tuning_path()
    
    #copy default file if no file exists in aws-lambda-power-tuning
    toml_path = os.path.join(power_tuning_path, 'samconfig.toml')
    if not os.path.exists(toml_path):
        default_path = os.path.join('.','Baas', 'samconfig.toml')
        shutil.copy(default_path, power_tuning_path)    

    #!!!the stack will need a name
    if "name" not in configs:
        if configs.keys() >= {"stack_name", "s3_prefix"}:
            raise Exception("the 'name' attribute has to be provided - alternatively 'stack_name' and and 's3_prefix' can be provided separately")
        else:
            configs.update("stack_name", configs["stack_name"])
            configs.update("s3_prefix", configs["s3_prefix"])
    else:
        configs.update({"stack_name":configs["name"]})
        configs.update({"s3_prefix":configs["name"]})
    
    #currently the name attribute overrides the single attributes - could of course be changed
    

    #open the default config and update it with the input configs
    with open(toml_path, 'r') as file:
        samconfig = toml.load(file)

    samconfig.update(configs)
    with open(toml_path, "w") as toml_file:
        toml.dump(samconfig, toml_file)

#build state machine
def build_statemachine():
    #go to the aws_lambda_power_tuning folder
    command = f"cd {get_power_tuning_path()} && sam deploy"
    output = subprocess.run(command, shell=True, capture_output=True, text=True)
    print("this is the stdout: " + output.stdout)
    print("this is the stderr: " + output.stderr)

#fill json for execution
    #strategy, memory configs to test, !!!lambda ARN!!! - might be known from the deploy
#TODO check for name of json
def fill_json(configs:dict):
    #TODO should first search for json in the aws-power-tuner-folder
    #read sample json
    sample_input_file = os.path.join('.', 'sample-execution-input.json')
    with open(sample_input_file, "r") as input_file:
            input = json.load(input_file)
    #getting the relevant info from the configs
    first_region = list(configs["AWS_regions"].keys())[0]
    wanted_keys = [configs['AWS_regions'][first_region]['memory_configurations'], 'lambda_ARN', 'strategy'] # The keys you want
    relevant_keys = dict((k, configs[k]) for k in wanted_keys if k in configs)        
    
    #update it using the right values
    input.update(relevant_keys)
    #write updated json back to the aws-power-tuner-folder
    new_input_file = os.path.join(get_power_tuning_path(), 'execution_input.json')

    with open(new_input_file, "w") as input_file:
        json.dump(input, input_file, indent=4)

#execute
def execute_power_tuning():
    pass