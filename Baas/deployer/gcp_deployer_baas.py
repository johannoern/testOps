import Baas.terraform as terraform
import Baas.deployer.memory_calculation as memory_calculation
import Baas.deployer.deployer_baas as deployer_baas
from Baas.deployer.deployer_baas_interface import deployer_baas_interface
from invoker.gcp_invoker import GCPInvoker

class GCP_deployer_baas(deployer_baas_interface):
    def __init__(self, handler, functions_src, region, project_id):
        self._handler = handler
        self._function_src = functions_src
        self._region = region
        self._project_id = project_id

    def add_terraform_snippet(self, terraform_dir):
        deployer_baas.add_terraform_snippets(terraform_dir, "gcp")

    def prepare_tfvars(self, function_name, terraform_dir,  memory_config:[int]=None):
        #0 add things that are not the function
        terraform.update_tfvars({"function_src": self._function_src, "region":self._region, "project": self._project_id}, terraform_dir, "gcp")
        
        #1. check for memory in function attributes
        if not memory_config == None:
            terraform.update_tfvars({"functions":[]}, terraform_dir, "gcp")
            for memory in memory_config:
                terraform.tfvars_add_function(function_name, self._handler, memory, terraform_dir, "gcp")
            return
        #2. check tfvars for existing config
        if terraform.get_tfvars(terraform_dir)["gcp"].get("functions",[]):
            return
        #3. check for exiting state
        tfstate = terraform.get_tfstate(terraform_dir)
        deployed_mem = deployer_baas.deployed_mem(tfstate, "google", "available_memory_mb")
        if deployed_mem:
            for memory in deployed_mem:
                terraform.tfvars_add_function(function_name, self._handler, memory, terraform_dir, "gcp")
            return
        #4. if no memory configs where found so far - turn to default
        terraform.tfvars_add_function(function_name, self._handler, 128, terraform_dir)

    #NOTE might be able to call generalized func - instead of duplicating code to gcp
    def memory_calculation(self, terraform_dir, function_name):

        invoker = GCPInvoker(gcp_project_id=self._project_id)
        min_speedup = 0.2

        min_mem = memory_calculation.get_smallest_memory(self, terraform_dir, function_name, invoker, "google", "gcp", "available_memory_mb")

        max_mem = memory_calculation.get_biggest_memory(self, terraform_dir, function_name, invoker, min_speedup, "google", "gcp", "available_memory_mb")


        terraform.terraform('apply', terraform_dir)
        print(f"min_mem: {min_mem}")
        print(f"max_mem: {max_mem}")