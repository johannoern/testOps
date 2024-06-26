import concurrent
import json
import logging
from datetime import datetime, timezone
from threading import current_thread
from time import perf_counter
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, wait

from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2 import service_account

from invoker.invoker_interface import InvokerInterface
from Gen_Utils import print_neat_dict


class GCPInvoker(InvokerInterface):

    def __init__(self, *, gcp_project_id: str):
        self.__project_name = gcp_project_id

    def run_experiment(self, *, deployment_dict: dict, payload: list, repetitions_of_experiment: int = 1,
                       repetitions_per_function: int = 2, concurrency: int = 1, **kwargs) -> Dict:
        #LATER why both logging and print 
        logging.debug('GCP::Run Experiment')
        print('GCP::Run Experiment')
        if 'GCP_regions' in deployment_dict:
            function_name = deployment_dict.get('function_name')
            for rep_experiment in range(repetitions_of_experiment):
                experiment_str = 'Experiment_' + str(rep_experiment)
                for region in deployment_dict['GCP_regions']:
                    print(region)
                    if rep_experiment == 0:
                        #TODO make sure output is checked
                        #TODO back to 50
                        for no_op_counter in range(5):
                            res = {'execution_start_utc': datetime.now(timezone.utc)}
                            start = perf_counter()
                            self.invoke_single_function(function_name='testOps_no_op_function', payload={}, region=region)
                            end = perf_counter()
                            res['execution_time'] = round((end - start) * 1000)
                            res['execution_end_utc'] = datetime.now(timezone.utc)
                            res['thread_name'] = f'testOps_no_op_function::{region}'
                            res['thread_ident'] = ''
                            dct = deployment_dict['GCP_regions'][region].get(experiment_str, {})
                            if not dct:
                                deployment_dict['GCP_regions'][region][experiment_str] = {'no_ops_function_' + str(no_op_counter): res}
                            else:
                                dct.update({'no_ops_function_' + str(no_op_counter): res})
                                deployment_dict['GCP_regions'][region][experiment_str] = dct
                    for mem_config in deployment_dict['GCP_regions'][region]['memory_configurations']:
                        if mem_config not in [128, 256, 512, 1024, 2048, 4096, 8192]:
                            continue
                        result_list = []
                        full_function_name = function_name + '_' + str(mem_config) + 'MB'
                        print(full_function_name)
                        start = perf_counter()
                        with ThreadPoolExecutor(max_workers=concurrency) as executor:
                            counter = 0
                            result = []
                            #NOTE rep_function is probably the same as counter also with more concurrency
                            for rep_function in range(repetitions_per_function):
                                future = executor.submit(self.__invoker_timed, full_function_name,
                                                              payload[counter % len(payload)], region)
                                
                                result.append(future)                               
                                
                                counter += 1
                                print(f"counter: {counter}\nrep_function: {rep_function}")

                            done, not_done = wait(result, return_when=concurrent.futures.ALL_COMPLETED)

                            for future in result:
                                result_list.append(future.result())

                        end = perf_counter()
                        print('time running:', end - start)
                        dct = deployment_dict['GCP_regions'][region].get(experiment_str, {})
                        if not dct:
                            deployment_dict['GCP_regions'][region][experiment_str] = {mem_config: result_list}
                        else:
                            dct.update({mem_config: result_list})
                            deployment_dict['GCP_regions'][region][experiment_str] = dct
        return deployment_dict

    def invoke_single_function(self, *, function_name: str, payload: Dict, region: str, **kwargs):

        url_adress = f'https://{region}-{self.__project_name}.cloudfunctions.net/{function_name}'

        creds = service_account.IDTokenCredentials.from_service_account_file(
            'google_credentials.json', target_audience=url_adress)

        authed_session = AuthorizedSession(creds)
        r = Request()
        creds.refresh(r)
        token = creds.token

        # make authenticated request

        response = authed_session.post(url_adress, json=payload)
        return response

#LATER why is invoke_single_function not used as with the aws invoker
    def __invoker_timed(self, function_name: str, payload: Dict, region: str) -> Dict:
        res = {'execution_start_utc': datetime.now(timezone.utc)}
        thread = current_thread()
        start = perf_counter()
        url_adress = f'https://{region}-{self.__project_name}.cloudfunctions.net/{function_name}'
        creds = service_account.IDTokenCredentials.from_service_account_file(
            'google_credentials.json', target_audience=url_adress)

        authed_session = AuthorizedSession(creds)
        r = Request()
        creds.refresh(r)

        #<class 'requests.models.Response'>
        response = authed_session.post(url_adress, json=payload)
        
        end = perf_counter()
        
        counter = 0
        
        res['execution_time'] = round((end - start) * 1000)
        res['execution_end_utc'] = datetime.now(timezone.utc)
        res['thread_name'] = thread.name
        res['thread_ident'] = thread.ident
        res['status_code'] = response.status_code
        print(response.content.decode('utf-8'))
        if response.status_code == 200:
            res['response'] = json.loads(response.content.decode('utf-8'))
        else:
            res['response'] = response.content.decode('utf-8')
        print(res['response'])
        return res

    def error(self, response):
        print("check if something went wrong")
        print(response)
        return not self.get_status_code(response)==200
    
    def get_status_code(self, response):
        return response.status_code     
