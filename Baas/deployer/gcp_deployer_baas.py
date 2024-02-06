from Baas import terraform
from Baas.deployer.deployer_baas_interface import deployer_baas_interface
from Baas.deployer import deployer_baas

class GCP_deployer_baas(deployer_baas_interface):
    def __init__(self, handler, functions_src, region, project_id):
        self.__handler = handler
        self.__function_src = functions_src
        self.__region = region
        self.__project_id = project_id
    
    def add_terraform_snippet(self, terraform_dir):
        deployer_baas.add_terraform_snippets(terraform_dir, "gcp")

    def prepare_tfvars(self, function_name, terraform_dir,  memory_config:[int]=None):
        #0 add things that are not the function
        terraform.update_tfvars({"function_src": self.__function_src, "region":self.__region, "project": self.__project_id}, terraform_dir, "gcp")
        
        #1. check for memory in function attributes
        if not memory_config == None:
            terraform.update_tfvars({"functions":[]}, terraform_dir, "gcp")
            for memory in memory_config:
                terraform.tfvars_add_function(function_name, self.__handler, memory, terraform_dir, "gcp")
            return
        #2. check tfvars for existing config
        if terraform.get_tfvars(terraform_dir)["gcp"].get("functions",[]):
            return
        #3. check for exiting state
        tfstate = terraform.get_tfstate(terraform_dir)
        deployed_mem = deployer_baas.deployed_mem(tfstate, "google", "available_memory_mb")
        if deployed_mem:
            for memory in deployed_mem:
                terraform.tfvars_add_function(function_name, self.__handler, memory, terraform_dir, "gcp")
            return
        #4. if no memory configs where found so far - turn to default
        terraform.tfvars_add_function(function_name, self.__handler, 128, terraform_dir)

    def memory_calculation():
        pass