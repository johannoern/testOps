from Baas.deployer.deployer_baas_interface import deployer_baas_interface
from .. import terraform
import os

def deploy(terraform_dir, function_name, providers:list[deployer_baas_interface], memory=None):
    #create terraform.tf
    create_terraformfile(terraform_dir, providers)
    
    #create tfvars
    for provider in providers:
        provider.prepare_tfvars(function_name, terraform_dir, memory)

    #find mem values smallest biggest

    #deploy
    terraform.terraform('apply', terraform_dir)


def create_terraformfile(terraform_dir, providers:list[deployer_baas_interface]):
    templates_path= os.path.join('.', 'Baas', 'templates')
    with open(os.path.join(terraform_dir, "terraform.tf"), 'w') as tf:
        with open(os.path.join(templates_path, 'global.txt')) as globals:
            tf.write(globals.read())
    for provider in providers:
        provider.add_terraform_snippet(terraform_dir)


def add_terraform_snippets(terraform_dir, provider):
    template_name = f"{provider}.txt"
    template_path = os.path.join('.', 'Baas', 'templates', template_name)
    with open(os.path.join(terraform_dir, "terraform.tf"), 'a') as tf:
        with open(os.path.join(template_path)) as provider:
            tf.write(provider.read())

def deployed_mem(tf_state:dict, provider, memory_attribute)->[int]:
    mem_configs = []
    try:
        for resource in tf_state["resources"]:
            if provider in resource["provider"] and resource["name"] == "test_subject" :
                for instance in resource["instances"]:
                    mem_configs.append(instance["attributes"][memory_attribute])
    except KeyError as e:
        print(f"{provider}: No functions deployed using default")
    print(f"{provider} deployed mem: {mem_configs}")
    return mem_configs
