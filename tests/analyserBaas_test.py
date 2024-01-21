import sys
import json
sys.path.insert(1, '../')
import Baas.analyserBaas as analyserBaas

def test_fill_json():
    analyserBaas.fill_json("lambdaARN")
