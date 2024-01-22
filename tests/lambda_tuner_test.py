import sys
import json
sys.path.insert(1, '../')
import Baas.aws_lambda_power_tuner as lambda_tuner

def test_fill_json():
    lambda_tuner.fill_json("lambdaARN")
