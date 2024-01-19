import json
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

#NOTE get rid of the shell=True and make it work independent of the platform

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

#worked 15.01. 19:04
#build state machine
def build_statemachine():
    #go to the aws_lambda_power_tuning folder
    command = f"cd {get_power_tuning_path()} && sam deploy"
    helpers.execute(command)

#fill json for execution
    #strategy, memory configs to test, !!!lambda ARN!!! - might be known from the deploy
#worked 15.01. 19:18
def fill_json(configs:dict):
    #read sample json
    sample_input_file = os.path.join(get_power_tuning_path(), 'scripts', 'sample-execution-input.json')
    with open(sample_input_file, "r") as input_file:
            input = json.load(input_file)
    #getting the relevant info from the configs
    #memory config
    first_region = list(configs["AWS_regions"].keys())[0]
    input.update({'powerValues':configs['AWS_regions'][first_region]['memory_configurations']})
    
    #updating rest #lambdaARN, strategy, payload, parallelInvocation
    wanted_keys = ['lambdaARN', 'strategy'] # The keys you want
    relevant_keys = dict((k, configs[k]) for k in wanted_keys if k in configs)        
    
    #update it using the right values
    input.update(relevant_keys)

    with open(sample_input_file, "w") as input_file:
        json.dump(input, input_file, indent=4)


#execute
def execute_power_tuning(configs:dict):
    script_path = os.path.join(get_power_tuning_path(), 'scripts')
    command = f"cd {script_path} && .\execute.sh {configs['name']} {configs['function_name']}"
    helpers.execute(command)
    output_file = os.path.join(get_power_tuning_path(), 'scripts', f'{configs["function_name"]}.json')
    with open(output_file, "r") as output:
            data = json.load(output)
            print(json.dumps(data, indent=4))
    return configs.update(data)
    
