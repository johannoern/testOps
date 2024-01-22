import json
import os
import sys
sys.path.insert(1, '../')
import Baas.aws_deploy_helpers as aws_helpers

def test_adapt_build_file():
    assert aws_helpers.adaptation_needed('./tests/helperdata')==True
    aws_helpers.adapt_build_file('./tests/helperdata', 'org.example.Main')
    assert aws_helpers.adaptation_needed('./tests/helperdata')==False
    #clean up
    with open('./tests/helperdata/build.gradle', 'w') as build:
        with open('./tests/helperdata/build.copy.gradle', 'r') as copy:
            content = copy.read()
            build.write(content)

#LATER does not check the file content
def test_implement_handler():
    aws_handler, aws_function_name = aws_helpers.implement_handler(get_config()["main_class"], get_config()["function_name"])
    handler_path = "./tests/helperdata/AWSRequestHandler.java"
    handler = "org.example.AWSRequestHandler"
    assert aws_handler.replace("\\", "/") == handler
    assert os.path.exists(handler_path)

    #clean up
    os.remove(handler_path)

def test_parse_main():
    package, output_type, inputs = aws_helpers.parse_main(get_config()["main_class"], get_config()["function_name"])
    assert package == "org.example"
    assert output_type == "String"
    assert inputs == 'String input'

def get_config():
    with open('./tests/helperdata/test_deployment.json') as data:
        return json.load(data)