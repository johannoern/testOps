import sys
import argparse
import jsonschema
from json import JSONDecodeError
from os.path import exists
import json
from typing import Dict
from Baas.builder.aws_builder_baas import AWS_builder_baas
from Baas.builder.gcp_builder_baas import GCP_builder_baas
from Baas.deployer.aws_deployer_baas import AWS_deployer_baas
from Baas.deployer.gcp_deployer_baas import GCP_deployer_baas

from Gen_Utils import print_neat_dict, export_json_to_file, create_credentials
from keep_mode import KeepMode
import deployer_v2
import invoker_v2
import analyzer_v2
import Baas.builder.builder_baas as builder_baas
import Baas.deployer.deployer_baas as deployer_baas
import logging


def int_try_parse(value):
    try:
        return isinstance(value, int)
    except ValueError:
        return False


def validate_json(candidate: str) -> Dict:
    dd = None
    try:
        with open(candidate, 'r') as f:
            dd = json.load(f)
    except JSONDecodeError as e:
        logging.error(e)
        print('Error reading %s. This could be due to a malformed file!' % candidate)
        sys.exit('Error loading input!')

    error_msg = None

    if dd.get('function_name', None) is None or  len(dd.get('function_name')) == 0:
        error_msg = 'Check function_name!'
    # if dd.get('no_op_code', None) is None:
    #     error_msg = 'Check no_op_code'

    contains_aws = dd.get('AWS_regions', 0) != 0
    contains_gcp = dd.get('GCP_regions', 0) != 0

    # if contains_aws:
    #     if dd.get('aws_handler', None) is None:
    #         error_msg = 'Check aws_handler'
    #     if dd.get('no_op_handler_aws', None) is None:
    #         error_msg = 'Check no_op_handler_aws'
    #     if dd.get('aws_code', None) is None:
    #         error_msg = 'Check aws_code'
    #     if dd.get('aws_runtime', None) is None:
    #         error_msg = 'Check aws_runtime'
    # if contains_gcp:
    #     if dd.get('gcp_handler', None) is None:
    #         error_msg = 'Check gcp_handler'
    #     if dd.get('no_op_handler_gcp', None) is None:
    #         error_msg = 'Check no_op_handler_gcp'
    #     if dd.get('gcp_code', None) is None:
    #         error_msg = 'Check gcp_code'
    #     if dd.get('gcp_runtime', None) is None:
    #         error_msg = 'Check gcp_runtime'
    # if dd.get('repetitions_of_experiment', None) is None or not int_try_parse(dd.get('repetitions_of_experiment')):
    #     error_msg = 'Check repetitions_of_experiment'
    # if dd.get('repetitions_per_function', None) is None or not int_try_parse(dd.get('repetitions_per_function')):
    #     error_msg = 'Check repetitions_per_function'
    # if dd.get('concurrency', None) is None or not int_try_parse(dd.get('concurrency')):
    #     error_msg = 'Check concurrency'
    # if dd.get('payload', None) is None or len(dd.get('payload')) == 0:
    #     error_msg = 'Check payload'

    if error_msg is not None:

        sys.exit('Error found in input.json! ' + error_msg)
    return dd


def print_config():
    print('Current configuration:')
    print('JSON: %s' % json_candidate)
    print('deploy %s' % deploy)
    print('invoke %s' % invoke)
    print('analyze %s' % analyze)
    print('keep mode %s' % keep_mode)

def validate_schema(schema_name: str, dict: dict):
    with open (f"./schemas/{schema_name}") as file:
        build_schema = json.load(file)
    try:
        jsonschema.validate(deployment_dict, build_schema)
        print("successfully validated")

    except jsonschema.exceptions.ValidationError as e:
        sys.exit(f"Validation against {schema_name} failed: {e.message}")

def populate_defaults(default_file: str, deployment_dict: dict):
    with open (f"./schemas/{default_file}") as file:
        defaults = json.load(file)    
    defaults.update(deployment_dict)
    return defaults

logging.basicConfig(filename='last_run.log', encoding='utf-8', level=logging.DEBUG, filemode='w')

json_candidate = None
#NOTE analyse is written differently should be coherent ...
deployment_dict:dict = None
build = False
deploy = False
invoke = False
analyze = False
baas_deploy = False
baas_analyse = False
plot = True
deploy_noop = True
keep_mode = KeepMode.KEEP_ALL

# parses arguments and defines cli
parser = argparse.ArgumentParser(description='A tool to aid with deployment and timing RTT of FaaS', epilog='Have a nice day!')
parser.add_argument('filename', help='Json input filename')
parser.add_argument('-b', '--build', action='store_true', help='Tells testOps to build gradle project')
parser.add_argument('-d', '--deploy', action='store_true', help='Tells testOps to deploy functions')
parser.add_argument('-i', '--invoke', action='store_true', help='Tells testOps to invoke and time functions')
parser.add_argument('-a', '--analyse', action='store_true', help='Tells testOps to analyse data either from the output of the -invoke option or the inputjson is no -invoke is present')
parser.add_argument('-keep', default='all', choices=['all', 'none', 'pareto'], help='Tells testops what to do with the deployed functions, the pareto option requires -a')
parser.add_argument('-d2', '--baas_deploy', action='store_true', help='tells testOps to deploy using terraform')
parser.add_argument('-a2', '--baas_analyse', action='store_true', help='uses powertuner to analyse the aws function')

#NOTE does not seem necessary
args = parser.parse_args()
if args.build:
    build = True
if args.deploy:
    deploy = True
if args.invoke:
    invoke = True
if args.analyse:
    analyze = True
if args.baas_deploy:
    baas_deploy = True
if args.baas_analyse:
    baas_analyse = True

json_candidate = args.filename
if args.keep == 'none':
    keep_mode = KeepMode.KEEP_NONE
elif args.keep == 'pareto':
    keep_mode = KeepMode.KEEP_PARETO

if exists(json_candidate):
    deployment_dict = validate_json(json_candidate)
else:
    raise FileNotFoundError('The file %s was not found!' % json_candidate)

if all(not task for task in [build, deploy, invoke, analyze, baas_deploy, baas_analyse]):
    print('You must pick at least one of the functions: build, deploy/deploy2, test, analyse/analyse2.')
    print('Aborting process! Have a nice day!')
    exit()

deployer_return = None
invoker_return = None
analyzer_return_dict = None
analyzer_return_pareto_et = None

#LATER print config feels like to much text in the console
print('All arguments ok:')
print_config()

#LATER validations in separate function
if build:
    deployment_dict = populate_defaults("build_default.json", deployment_dict)
    validate_schema("build_schema.json", deployment_dict)  
    builders = []
    if "aws" in deployment_dict["provider"]:
        builders.append(AWS_builder_baas("aws"))
    if "gcp" in deployment_dict["provider"]:
        builders.append(GCP_builder_baas("gcp"))
    deployment_dict.update(builder_baas.build(deployment_dict["project_path"], deployment_dict["main_class"],
                                              deployment_dict["function_name"], builders))

if baas_deploy:
    deployment_dict = populate_defaults("deploy_default.json", deployment_dict)
    validate_schema("deploy_schema.json", deployment_dict)
    providers = []
    if "aws" in deployment_dict["provider"]:
        providers.append(AWS_deployer_baas(deployment_dict["aws_handler"], deployment_dict["aws_code"],
                                           deployment_dict["aws_region"]))
    if "gcp" in deployment_dict["provider"]:
        providers.append(GCP_deployer_baas(deployment_dict["gcp_handler"], deployment_dict["gcp_code"],
                                           deployment_dict["gcp_region"], deployment_dict["gcp_project_id"]))
    deployer_baas.deploy(deployment_dict["terraform_dir"], deployment_dict["function_name"],
                         providers, deployment_dict["payload"], deployment_dict["memory"])
    # deployer_baas.create_terraformfile(deployment_dict["terraform_dir"], deployment_dict["provider"])
    # deployer_baas.prepare_tfvars_aws(deployment_dict["aws_handler"], deployment_dict["function_name"],
    #                                 deployment_dict["terraform_dir"], deployment_dict["old_analyser"],
    #                                  deployment_dict["aws_region"],
    #                                 deployment_dict["aws_code"], deployment_dict.get('memory_configurations', None))
    # deployer_baas.prepare_tfvars_gcp(deployment_dict["gcp_handler"], deployment_dict["function_name"],
    #                                 deployment_dict["gcp_project_id"], deployment_dict["terraform_dir"],
    #                                 deployment_dict["old_analyser"], deployment_dict["gcp_region"],
    #                                 deployment_dict["gcp_code"], deployment_dict.get('memory_configurations', None),)
    # arns = deployer_baas.terraform('apply', deployment_dict["terraform_dir"])
    # try:
    #     arn = arns[deployment_dict["function_name"]]
    #     deployment_dict.update({"lambdaARN":arn})
    # except KeyError:
    #     print("analyse2 will not be possible, because old_analyser was set to True")

    with open(json_candidate, "w") as json_file:
        json.dump(deployment_dict, json_file, indent=4)

if deploy:
    create_credentials()
    deployer_return = deployer_v2.deploy_function(deployment_dict, deploy_no_op=deploy_noop)

if invoke:
    # populate_defaults("invoke_default.json", deployment_dict)
    create_credentials()
    if deployer_return is not None:
        invoker_return = invoker_v2.run_experiment(deployer_return)
    else:
        invoker_return = invoker_v2.run_experiment(deployment_dict)

if analyze:

    if invoker_return is not None:
        analyzer_return_list, analyzer_return_pareto_et, analyzer_return_pareto_rtt = analyzer_v2.analyze(invoker_return, plot=plot)
    else:
        analyzer_return_list, analyzer_return_pareto_et, analyzer_return_pareto_rtt = analyzer_v2.analyze(deployment_dict, plot=plot)

    flat_return_list = []
    for prov in analyzer_return_list:
        for x in prov:
            flat_return_list.append(x)

    deletion_candidates = flat_return_list.copy()
    pareto_rows_et = []
    pareto_rows_rtt = []
    for row in analyzer_return_pareto_et.itertuples():
        for item in deletion_candidates:
            if row[1] == item.get('avg_ET') and row[2] == item.get('cost'):
                deletion_candidates.pop(deletion_candidates.index(item))
                pareto_rows_et.append(item)
                continue

    for row in analyzer_return_pareto_rtt.itertuples():
        for item in flat_return_list:
            if row[1] == item.get('avg_RTT') and row[2] == item.get('cost'):
                pareto_rows_rtt.append(item)
                continue

    if keep_mode == KeepMode.KEEP_PARETO:
        if len(deletion_candidates) > 0:
            deployer_v2.delete_function(deployment_dict=deployment_dict, pareto=deletion_candidates)
# handles output.txt file
    orig_stdout = sys.stdout
    output_filename = deployment_dict['function_name'] + '_output.txt'
    with open(output_filename, 'w') as f:
        sys.stdout = f
        print('Pareto Cost - ET')
        print(analyzer_return_pareto_et, '\n')
        print('Pareto measurements ET')
        for x in pareto_rows_et:
            print(x)
        print('\n')
        print('Pareto Cost - RTT')
        print(analyzer_return_pareto_rtt, '\n')
        print('Pareto measurements RTT')
        for x in pareto_rows_rtt:
            print(x)
        print('\n')
        print('Analyzer measurements')
        for x in flat_return_list:
            print(x)
        sys.stdout = orig_stdout

    print('Pareto measurements ET')
    for x in pareto_rows_et:
        print(x)
    print('\n')
    print('Pareto measurements RTT')
    for x in pareto_rows_rtt:
        print(x)
    print('\n')
    print('Analyzer measurements')
    for x in flat_return_list:
        print(x)
    f.close()

if keep_mode == KeepMode.KEEP_NONE:
    deployer_v2.delete_function(deployment_dict=deployment_dict)


if baas_analyse:
    print("baas_analyse temporarily disabled")
    # with open ("./schemas/deploy_schema.json") as file:
    #     build_schema = json.load(file)
    # try:
    #     jsonschema.validate(deployment_dict, build_schema)

    # except jsonschema.exceptions.ValidationError as e:
    #     sys.exit(f"Validation failed: {e.message}")

    # if(deployment_dict.get("powertuner_setup", False)):
    #     print("setup (cloning repo and building statemachine) was already done\nIf it should be repeated change 'powertuner_setup' to False")
    # else:
    #     lambda_tuner.powertuner_setup()
    #     deployment_dict.update(lambda_tuner.create_config_file(deployment_dict))
    #     lambda_tuner.build_statemachine()
    # lambda_tuner.fill_json(deployment_dict["lambdaARN"])
    # lambda_tuner.execute_power_tuning(deployment_dict['function_name'], deployment_dict.get('stack_name', deployment_dict['name']))
#safe the additions to the json file
export_json_to_file(json_candidate, deployment_dict)


