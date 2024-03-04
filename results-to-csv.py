import csv
import os
import json

another_file = True

while another_file:
    file = input("file to be appended:\n")

    # Data to be appended (as a list of dictionaries)
    with open (file, 'r') as data:
        results = json.load(data) 

    new_data = []

    #aws
    aws_memory = results["AWS_regions"]["us-east-1"]["memory_configurations"]
    for mem in aws_memory:
        function_run = results["AWS_regions"]["us-east-1"]["Experiment_0"][f"{mem}"]
        for result in function_run:
            if "errorType" in result["response"]["Payload"]:
                    line = {'func_provider': 'aws', 'func_mem': mem, 'file_size': 0, 'src_provider': 'unknown',
                    'dest_provider':'unknown', 'same_region': False,
                    'upload_time': 0, 'download_time': 0}
                    new_data.append(line)
                    continue
            file_size = result["response"]["Payload"]["sourceFile"][4:-4]
            line = {'func_provider': 'aws', 'func_mem': mem, 'file_size': file_size, 'src_provider': result["response"]["Payload"]["srcProvider"],
                    'dest_provider':result["response"]["Payload"]["destProvider"], 'same_region': False,
                    'upload_time': result["response"]["Payload"]["uploadTime"], 'download_time': result["response"]["Payload"]["downloadTime"]}
            new_data.append(line)

    #gcp
    gcp_memory = results["GCP_regions"]["us-central1"]["memory_configurations"]
    for mem in gcp_memory:
        function_run = results["GCP_regions"]["us-central1"]["Experiment_0"][f"{mem}"]
        for result in function_run:
            if not result["status_code"] == 200:
                    line = {'func_provider': 'gcp', 'func_mem': mem, 'file_size': 0, 'src_provider': 'unknown',
                    'dest_provider':'unknown', 'same_region': True,
                    'upload_time': 0, 'download_time': 0}
                    new_data.append(line)
                    continue
            try:
                file_size = result["response"]["sourceFile"][4:-4]
                line = {'func_provider': 'gcp', 'func_mem': mem, 'file_size': file_size, 'src_provider': result["response"]["srcProvider"],
                        'dest_provider':result["response"]["destProvider"], 'same_region': True,
                        'upload_time': result["response"]["uploadTime"], 'download_time': result["response"]["downloadTime"]}
            except KeyError as e:
                 print(e)
                 print(f"KeyError occured for: {result}")
                 continue
            new_data.append(line)

    # Specify the file name
    file_name = 'bandwidth_results.csv'

    # Specify the field names
    fieldnames = ['func_provider', 'func_mem', 'file_size', 'src_provider', 'dest_provider', 'same_region', 'upload_time', 'download_time']

    # Check if the file exists
    file_exists = os.path.isfile(file_name)

    # Appending to the existing CSV file or creating a new one
    with open(file_name, 'a+', newline='') as csvfile:
        csv_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # If the file is empty or doesn't exist, write the header
        if not file_exists or csvfile.tell() == 0:
            csv_writer.writeheader()
        
        # Append the new data rows
        csv_writer.writerows(new_data)
    
    more = input("Do you want to append another file? yes/no\n")
    if not more == 'yes':
        another_file = False