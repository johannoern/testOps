import json
tfvars_path = ".\\terraform\\terraform.tfvars.json"
    #try reading existing vars
with open(tfvars_path) as tfvars_file:
    tfvars = json.load(tfvars_file)
    print("Here is the data from the tfvars:")
    print(tfvars)