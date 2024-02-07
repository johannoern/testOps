import json
from python_terraform import Terraform
import Gen_Utils

#run terraform file
#NOTE would be nicer with terraform_python    
def terraform(command: str, terraform_dir):
    tf = Terraform(working_dir=terraform_dir)
    Gen_Utils.execute(f"cd {terraform_dir} && terraform init")

    if command =='plan':
        print("terraform plan")
        Gen_Utils.execute(f"cd {terraform_dir} && terraform plan")
        return

    if command =='apply':
        print("terraform apply")
        Gen_Utils.execute(f"cd {terraform_dir} && terraform apply")
        output = tf.output(capture_output = True)
        return output["lambda_arns"]["value"]

    if command =='destroy':
        print("terraform destroy")
        Gen_Utils.execute(f"cd {terraform_dir} && terraform destroy")
        return

def get_tfvars(terraform_dir):
    tfvars_path = f"{terraform_dir}\\terraform.tfvars.json"
    try:
        with open(tfvars_path, 'r') as tfvars_file:
            tfvars:dict = json.load(tfvars_file)
    except FileNotFoundError:
        tfvars:dict = {}
        with open(tfvars_path, 'w') as tfvars_file:
            tfvars_file.write("{}")
    return tfvars

def get_tfstate(terraform_dir):
    tfstate_path = f"{terraform_dir}\\terraform.tfstate"
    try:
        with open(tfstate_path, 'r') as tfvars_file:
            tfstate:dict = json.load(tfvars_file)
    except FileNotFoundError:
        return None
    return tfstate

def write_tfvars(tfvars_path, tfvars): 
    with open(tfvars_path, "w") as tfvars_file:
        json.dump(tfvars, tfvars_file, indent=4)

def update_tfvars(update:dict, terraform_dir, provider):
    tfvars = get_tfvars(terraform_dir)
    tfvars.setdefault(provider, {})
    tfvars[provider].update(update)
    write_tfvars(f"{terraform_dir}\\terraform.tfvars.json", tfvars)

def tfvars_add_function(function_name, handler, memory, terraform_dir, provider:str):
    tfvars = get_tfvars(terraform_dir)

    print(f"adding function {provider} {memory}")
    functions: dict = tfvars[provider].get("functions", [])
    new_function = {"handler":handler, "function_name":f"{function_name}_{memory}MB", "memory":memory, "timeout": 3}
    if new_function not in functions:
        functions.append(new_function)
    tfvars[provider].update({"functions":functions})
    write_tfvars(f"{terraform_dir}\\terraform.tfvars.json", tfvars)

def tfvars_delete_function(function_name, handler, memory, terraform_dir, provider:str):
    tfvars = get_tfvars(terraform_dir)

    print(f"deleting function {provider} {memory}")
    functions: dict = tfvars[provider].get("functions", [])
    old_function = {"handler":handler, "function_name":f"{function_name}_{memory}MB", "memory":memory, "timeout": 3}
    functions.remove(old_function)
    tfvars[provider].update({"functions":functions})
    write_tfvars(f"{terraform_dir}\\terraform.tfvars.json", tfvars)

