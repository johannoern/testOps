from Baas import terraform
import Baas.deployer.deployer_baas as deployer_baas


def get_smallest_memory(self, terraform_dir, function_name, invoker, provider_state, provider_vars, mem_attribute):
    tf_state = terraform.get_tfstate(terraform_dir)
    deployed_mem = deployer_baas.deployed_mem(tf_state, provider_state, mem_attribute)
    if not deployed_mem:
        terraform.terraform('apply', terraform_dir)
        tf_state = terraform.get_tfstate(terraform_dir)
        deployed_mem = deployer_baas.deployed_mem(tf_state, provider_state, mem_attribute)
    min_mem = min(deployed_mem)

    time, response = deployer_baas.invoke_function(function_name, self._region, invoker, min_mem)
    status_code = invoker.get_status_code(response)
    if status_code == 200:
        while not min_mem == 128 and status_code ==200:
            if not min_mem == 128:
                min_mem = min_mem//2
                #tfvars add function
                terraform.tfvars_add_function(function_name, self._handler, min_mem, terraform_dir, provider_vars)
                #terrform deploy
                terraform.terraform('apply', terraform_dir)
                #test_function
                time, response = deployer_baas.invoke_function(function_name, self._region, invoker, min_mem)
                status_code = invoker.get_status_code(response)
                if not status_code ==200:
                    terraform.tfvars_delete_function(function_name, self._handler, min_mem, terraform_dir, provider_vars)
                    min_mem = min_mem*2
        print(f"{provider_vars} min_mem = {min_mem}")
        return min_mem
    else:
        #NOTE this will always increase the memory but the function might fail for different reason
        while not status_code==200:
            terraform.tfvars_delete_function(function_name, self._handler, min_mem, terraform_dir, provider_vars)
            min_mem = min_mem*2
            if not min_mem in deployed_mem:
                #tfvars add function
                terraform.tfvars_add_function(function_name, self._handler, min_mem, terraform_dir, provider_vars)
                #terrform deploy
                terraform.terraform('apply', terraform_dir)

            time, response = deployer_baas.invoke_function(function_name, self._region, invoker, min_mem)
            status_code = invoker.get_status_code(response)
            if status_code==200:
                print(f"{provider_vars} min_mem = {min_mem}")
                return min_mem
                
def get_biggest_memory(self, terraform_dir, function_name, invoker, min_speedup, provider_state, provider_vars, mem_attribute):
    tf_state = terraform.get_tfstate(terraform_dir)
    deployed_mem = deployer_baas.deployed_mem(tf_state, provider_state, mem_attribute)
    max_mem = min(deployed_mem)
    current_time, response = deployer_baas.invoke_function(function_name, self._region, invoker, max_mem)
    last_time = current_time*2

    while not current_time>last_time*(1-min_speedup):
        print(f"with {max_mem} the execution time was: {current_time}")
        max_mem = max_mem*2
        if not max_mem in deployed_mem:
            #tfvars add function
            terraform.tfvars_add_function(function_name, self._handler, max_mem, terraform_dir, provider_vars)
            #terrform deploy
            terraform.terraform('apply', terraform_dir)
        last_time = current_time
        current_time, response = deployer_baas.invoke_function(function_name, self._region, invoker, max_mem)
    
    
    max_mem = max_mem//2
    for function in terraform.get_tfvars(terraform_dir)[provider_vars]["functions"]:
        if function["memory"]>max_mem:
            terraform.tfvars_delete_function(function_name, self._handler, function["memory"], terraform_dir, provider_vars)
    print(f"{provider_vars} max_mem = {max_mem}")
    return max_mem