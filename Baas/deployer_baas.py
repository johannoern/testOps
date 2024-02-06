import datetime
import json
import os
import re
from time import perf_counter
from Gen_Utils import print_neat_dict
from invoker import *
from Baas import helpers
from python_terraform import Terraform

#LATER possible it is nicer to use logging instead of print ...
#this file deploys your function using terrafrom
#prerequisite terraform

def create_terraformfile(terraform_dir, providers):
    templates_path= os.path.join('.', 'Baas', 'templates')
    with open(os.path.join(terraform_dir, "terraform.tf"), 'w') as tf:
        with open(os.path.join(templates_path, 'global.txt')) as globals:
            tf.write(globals.read())
    
    for provider in providers:
        add_provider_tf(provider, terraform_dir)

#TODO make sure tfvars include the providers with necessary inputs
def add_provider_tf(provider, terraform_dir):
    templates_path= os.path.join('.', 'Baas', 'templates')
    with open(os.path.join(terraform_dir, "terraform.tf"), 'a') as tf:
        with open(os.path.join(templates_path, f'{provider}.txt')) as provider:
            tf.write(provider.read())
        

#NOTE may be variables should be overwritten rather than updated
def prepare_tfvars_aws(aws_handler, aws_function_name, terraform_dir, old_analyser, region, aws_code=None, mem_config=None):       
    #TODO would be nice if it was aws instead of amazon...
    provider = "amazon"
    
    #TODO check if source has changed if not this has to be skipped, also skip process if mem_config was given
    print("preparing_tfvars_aws")
    #terraform_dir
    tfvars = get_tfvars(terraform_dir)
    tfstate = get_tfstate(terraform_dir)
    #aws_code
    aws_function_src = get_function_src(aws_code, tfvars, provider)

    tfvars_update = {"region":region, "function_src":aws_function_src}

    try:
        tfvars[provider].update(tfvars_update)
    except KeyError:
        tfvars.update({provider:tfvars_update})

#TODO horrible amazon should just be aws also in the tf vars
    if provider == "amazon":
        provider_state_file = "aws"
    else:
        provider_state_file = provider

    
    deployed_mem = get_mem_configs(tfstate, provider_state_file)

    if not deployed_mem:
        default_mem = 128
        print(f"deploy default mem: {default_mem}")
        tfvars = deploy_function(aws_function_name, aws_handler, default_mem, tfvars,
                            terraform_dir, provider)
        deployed_mem = get_mem_configs(tfstate, provider_state_file)

    smallest_memory = find_smallest_memory(aws_function_name, region, deployed_mem, terraform_dir, tfvars, aws_handler, provider, AWSInvoker())
    print(f"this is the smallest memory: {smallest_memory}")

    deployed_mem = get_mem_configs(tfstate, provider_state_file)

    print("deployed after smallest_mem")
    print(deployed_mem)

    biggest_memory = find_biggest_memory(aws_function_name, region, deployed_mem, terraform_dir, tfvars, aws_handler, provider, AWSInvoker())
    print(f"this is the biggest memory: {biggest_memory}")

    functions = get_tfvars(terraform_dir)[provider]["functions"]

    if not old_analyser:
        memory = 256
        functions.append({"handler":aws_handler, "function_name":aws_function_name, "memory":memory, "timeout": 3})
    
    tfvars[provider].update({"functions":functions})
    write_tfvars(f"{terraform_dir}\\terraform.tfvars.json", tfvars)

def prepare_tfvars_gcp(gcp_handler, gcp_function_name, gcp_project_id, terraform_dir, old_analyser, region, gcp_code=None, mem_configs=None):
    provider = "gcp"
    #TODO check if source has changed if not this has to be skipped, also skip process if mem_config was given
    print("preparing_tfvars_gcp")
    #terraform_dir
    tfvars:dict = get_tfvars(terraform_dir)
    tfstate:dict = get_tfstate(terraform_dir)
    #gcp_code
    gcp_function_src = get_function_src(gcp_code, tfvars, provider)

    tfvars_update = {"region":region, "function_src":gcp_function_src, "project":gcp_project_id, "function_src": gcp_function_src}
    
    try:
        tfvars[provider].update(tfvars_update)
    except KeyError:
        tfvars.update({provider:tfvars_update})

    deployed_mem = get_mem_configs(tfstate, provider)

    if not deployed_mem:
        deployed_mem = [128]
        print("no mem found deploying first function")
        deploy_function(gcp_function_name, gcp_handler, 128, tfvars, terraform_dir, provider)

    smallest_memory = find_smallest_memory(gcp_function_name, region, deployed_mem, terraform_dir, tfvars, gcp_handler, provider, GCPInvoker(gcp_project_id=gcp_project_id))
    print(f"this is the smallest memory: {smallest_memory}")

    deployed_mem = get_mem_configs(tfstate, provider)

    biggest_memory = find_biggest_memory(gcp_function_name, region, deployed_mem, terraform_dir, tfvars, gcp_handler,provider, GCPInvoker(gcp_project_id=gcp_project_id))
    print(f"this is the biggest memory: {biggest_memory}")

    functions = get_tfvars(terraform_dir)[provider]["functions"]

    if not old_analyser:
        memory = 256
        functions.append({"handler":gcp_handler, "function_name":gcp_function_name, "memory":memory, "timeout": 3})
    
    tfvars[provider].update({"functions":functions})
    write_tfvars(f"{terraform_dir}\\terraform.tfvars.json", tfvars)


"""helpers for tfvars"""
def get_function_src(code, tfvars, provider):
    if not code == None:
        return code
    else:
        print(f"no code passed for {provider}. Trying to find it in the terrform variables")
        try:
            function_src = tfvars[provider]["function_src"]
        except KeyError as e:
            raise ValueError(f"{e.message}\n after testops build code variables are set automatically") from e
        return function_src

#get the deployed mem sizes for given provider
#provider options are google and aws
def get_mem_configs(tf_state:dict, provider):
    mem_configs = []
    #TODO change this logic
    if provider == "aws":
        mem = "memory_size"
    else:
        mem = "available_memory_mb"
    try:
        for resource in tf_state["resources"]:
            if provider in resource["provider"] and resource["name"] == "test_subject" :
                for instance in resource["instances"]:
                    mem_configs.append(instance["attributes"][mem])
    except KeyError as e:
        print("Nothing is deployed. Memory calculations are starting")
    print(f"deployed mem: {mem_configs}")
    return mem_configs

#deployed mem comes from tfstate - cannot be empty
def find_smallest_memory(function_name, region, deployed_mem:list, terraform_dir, tfvars, handler, provider, invoker:InvokerInterface):
    print("find_smallest_memory")
    failed_runs=0
    #Test smallest deployed memory
    while True:
        smallest_memory:int = min(deployed_mem)
        name = f"{function_name}_{smallest_memory}MB"
        response = invoker.invoke_single_function(function_name = name, payload = None, region = region)
        status_code = invoker.get_status_code(response)
        if status_code == 200:
            if not failed_runs==0 or smallest_memory == 128:
                return smallest_memory
            else:
                smallest_memory = smallest_memory//2
                deployed_mem.append(smallest_memory)
                tfvars = deploy_function(function_name, handler, smallest_memory, tfvars,
                                         terraform_dir, provider)
        else:
            #NOTE too small memory is not the only reason a function might fail may be take that into account
            failed_runs+=1
            for function in tfvars[provider]["functions"]:
                if function["memory"] == smallest_memory:
                    tfvars[provider]["functions"].remove(function)
            smallest_memory*=2
            if smallest_memory in deployed_mem:
                return smallest_memory
            else:
                deployed_mem.append(smallest_memory)
                tfvars = deploy_function(function_name, handler, smallest_memory, tfvars,
                                         terraform_dir, provider)
                
def find_biggest_memory(function_name, region, deployed_mem:list, terraform_dir, tfvars, handler, provider, invoker):
    print("find_biggest_memory")
    biggest_memory = max(deployed_mem)
    if biggest_memory == 128:
        biggest_memory = 256
        deploy_function(function_name, handler, biggest_memory, tfvars, terraform_dir, provider)
        
    execution_time_last_round = invoke_timed(function_name, region, invoker, int(biggest_memory//2))
    min_improvement = 0.2
    while True:
        execution_time = invoke_timed(function_name, region, invoker, biggest_memory)
        execution_time = invoke_timed(function_name, region, invoker, biggest_memory)
        print(f"execution_time_last_round: {execution_time_last_round}")
        print(f"execution_time: {execution_time}")
        improvement = 1-(execution_time/execution_time_last_round)
        print(f"improvement: {improvement}")
        #checks
        if  improvement<min_improvement:
            for function in tfvars[provider]["functions"]:
                mem = function["memory"]
                if mem == biggest_memory:
                    tfvars[provider]["functions"].remove(function)
                    write_tfvars(f"{terraform_dir}\\terraform.tfvars.json", tfvars)
                    return biggest_memory//2
        if biggest_memory == 8192:
            return biggest_memory
        
        #prepare next iteration
        execution_time_last_round = execution_time
        biggest_memory = biggest_memory*2
        
        deploy_function(function_name, handler, biggest_memory, tfvars, terraform_dir, provider)

def invoke_timed(function_name, region, aws, memory):
    name = f"{function_name}_{memory}MB"
    aws.invoke_single_function(function_name = name, payload = None, region = region)
    start = perf_counter()
    aws.invoke_single_function(function_name = name, payload = None, region = region)
    end = perf_counter()
    return round((end - start) * 1000)



#Line 276 02.02.2024 17:04