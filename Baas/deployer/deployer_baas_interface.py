from abc import ABC, abstractmethod

class deployer_baas_interface(ABC):
    @abstractmethod
    def __init__(self, handler, functions_src, region):
        pass

    @abstractmethod
    def add_terraform_snippet(self, terraform_dir):
        '''
        puts the snippet into the terraform.tf file
        if a provider is not needed the snippet will not be there and
        terraform cannot complain about the missing variables
        '''
        pass    
    
    @abstractmethod
    def prepare_tfvars(self, function_name:str, terraform_dir:str, memory_config:[int]=None):
        '''
        function that fills the tfvariables to be ready to deploy
        looks in following places to find info
        1. input.json
        2. existing tfvars
        3. existing tfstate
        4. adds empty array {"functions":[]} memory calculations will deploy with 128MB to get started
        '''
        pass

    @abstractmethod
    def memory_calculation():
        '''
        calculates the min. memory needed
        calcualtes the max. memory sensible
        '''
        pass