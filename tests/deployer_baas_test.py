import sys
import json
import os
import pytest
from Gen_Utils import print_neat_dict
sys.path.insert(1, '../')
import Baas.deployer_baas as deployer_baas

def test_build():
    pass

def test_create_terraformfile():
    pass

def test_add_provider_tf():
    pass

def test_prepare_tfvars_aws():
    pass

def test_prepare_tfvars_gcp():
    pass

#NOTE probably not really worth testing
def text_terraform():
    pass

def test_get_tfvars():
    pass

def test_get_tfstate():
    pass

def test_get_function_src():
    pass

def test_get_mem_config():
    state = get_tfstate()
    deployed_mem = deployer_baas.get_mem_configs(state, "aws")
    assert deployed_mem == [128,256]
    deployed_mem = deployer_baas.get_mem_configs(state, "gcp")
    assert deployed_mem == [128,256]


def test_find_smallest_memory():
    pass

def test_find_biggest_memory():
    pass
 #NOTE probably also hard to test
def test_invoke_timed():
    pass

#NOTE again hard to test
def test_deploy_function():
    pass

def test_write_tfvars():
    pass

def test_read_gradle_version():
    pass


def get_config():
    with open('./tests/helperdata/test_deployment.json') as data:
        return json.load(data)
    
def get_tfstate():
    with open('./tests/helperdata/test.tfstate') as data:
        return json.load(data)
    
