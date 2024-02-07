import Baas.terraform as terraform
import Baas.deployer.memory_calculation as memory_calculation
import Baas.deployer.deployer_baas as deployer_baas
from Baas.deployer.deployer_baas_interface import deployer_baas_interface
from invoker.aws_invoker import AWSInvoker

class AWS_deployer_baas(deployer_baas_interface):
    def __init__(self, handler, functions_src, region):
        self._handler = handler
        self._function_src = functions_src
        self._region = region 
    
    def add_terraform_snippet(self, terraform_dir):
        deployer_baas.add_terraform_snippets(terraform_dir, "aws")
    
    def prepare_tfvars(self, function_name, terraform_dir,  memory_config:[int]=None):
        #0 add things that are not the function
        terraform.update_tfvars({"function_src": self._function_src, "region":self._region}, terraform_dir, "amazon")
        
        #1. check for memory in function attributes
        if not memory_config == None:
            terraform.update_tfvars({"functions":[]}, terraform_dir, "amazon")
            for memory in memory_config:
                terraform.tfvars_add_function(function_name, self._handler, memory, terraform_dir, "amazon")
            return
        #2. check tfvars for existing config
        if terraform.get_tfvars(terraform_dir)["amazon"].get("functions",[]):
            return
        #3. check for exiting state
        tfstate = terraform.get_tfstate(terraform_dir)
        deployed_mem = deployer_baas.deployed_mem(tfstate, "aws", "memory_size")
        if deployed_mem:
            for memory in deployed_mem:
                terraform.tfvars_add_function(function_name, self._handler, memory, terraform_dir, "amazon")
            return
        #4. if no memory configs where found so far - turn to default and deploy else nothing is deployed
        terraform.tfvars_add_function(function_name, self._handler, 128, terraform_dir)

    #NOTE might be able to call generalized func - instead of duplicating code to gcp
    def memory_calculation(self, terraform_dir, function_name):
        invoker = AWSInvoker()
        min_speedup = 0.2

        min_mem = memory_calculation.get_smallest_memory(self, terraform_dir, function_name, invoker, "aws", "amazon", "memory_size")

        max_mem = memory_calculation.get_biggest_memory(self, terraform_dir, function_name, invoker, min_speedup, "aws", "amazon", "memory_size")

        terraform.terraform('apply', terraform_dir)
        print(f"min_mem: {min_mem}")
        print(f"max_mem: {max_mem}")