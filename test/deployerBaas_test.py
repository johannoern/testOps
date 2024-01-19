import sys
import json
import os
import pytest
sys.path.insert(1, '../')
import Baas.deployerBaas as deployerBaas


def test_adapt_build_file():
    assert deployerBaas.adaptation_needed('./tests/helperdata')==True
    deployerBaas.adapt_build_file('./tests/helperdata', 'org.example.Main')
    assert deployerBaas.adaptation_needed('./tests/helperdata')==False
    #clean up
    with open('./tests/helperdata/build.gradle', 'w') as build:
        with open('./tests/helperdata/build.copy.gradle', 'r') as copy:
            content = copy.read()
            build.write(content)

#LATER does not check the file content
def test_implement_handler():
    new_config = deployerBaas.implement_handler(get_config())
    handler_path = "./tests/helperdata/AWSRequestHandler.java"
    assert new_config["main_class"].replace("\\", "/") == handler_path
    assert os.path.exists(handler_path)

#only works if there is a real gradle project in the test_deployment.json
def test_build():
    output = deployerBaas.build(get_config())
    assert output['aws_code']=="C:/Users/Johann/Documents/uibk/BachelorArbeit/testOpsGradleImpl/build/libs/testOpsGradleImpl-1.0-SNAPSHOT.jar"

def test_write_tfvars():
    tfvars_path = './tests/helperdata/terraform.tfvars.json'
    values = get_config()
    #check that tfvars does not exist
    assert os.path.exists(tfvars_path) == False

    expected_msg = "KeyError: Key 'aws_code' is required but not found.\n after testops build 'aws_code' is set automatically"
    with pytest.raises(ValueError, match = expected_msg):
        deployerBaas.write_tfvars(values)

    values.update({"aws_code": "aws/code/is_here"})

    deployerBaas.write_tfvars(values)
    #check that it exists
    assert os.path.exists('./tests/helperdata/terraform.tfvars.json') == True
    with open(tfvars_path) as tfvars:
        tfvars_data = json.load(tfvars)
    assert tfvars_data["amazon"]["function_src"] == values["aws_code"]

    #clean up
    os.remove(tfvars_path)
    assert os.path.exists('./tests/helperdata/terraform.tfvars.json') == False

def test_terraform():
    deployerBaas.terraform("plan")

def get_config():
    with open('./tests/helperdata/test_deployment.json') as data:
        return json.load(data)