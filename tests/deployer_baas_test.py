import sys
import json
import os
import pytest
sys.path.insert(1, '../')
import Baas.deployerBaas as deployerBaas

#only works if there is a real gradle project in the test_deployment.json
def test_write_tfvars():
    tfvars_path = './tests/helperdata/terraform.tfvars.json'
    values = get_config()
    # check that tfvars does not exist
    assert os.path.exists(tfvars_path) == False

    expected_msg = "KeyError: Key 'aws_code' is required but not found.\n after testops build 'aws_code' is set automatically"
    with pytest.raises(ValueError, match = expected_msg):
        deployerBaas.prepare_tfvars_aws(values["aws_handler"], values["function_name"], values["terraform_dir"])

    values.update({"aws_code": "aws/code/is_here"})

    deployerBaas.prepare_tfvars_aws(values["aws_handler"], values["function_name"], values["terraform_dir"], values["aws_code"])
    #check that it exists
    assert os.path.exists('./tests/helperdata/terraform.tfvars.json') == True
    with open(tfvars_path) as tfvars:
        tfvars_data = json.load(tfvars)
    assert tfvars_data["amazon"]["function_src"] == values["aws_code"]

    #clean up
    os.remove(tfvars_path)
    assert os.path.exists('./tests/helperdata/terraform.tfvars.json') == False

def test_get_mem_configs():
    pass

def get_config():
    with open('./tests/helperdata/test_deployment.json') as data:
        return json.load(data)
    
