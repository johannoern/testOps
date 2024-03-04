import mysql.connector
import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression


def linreg(file_size, times, title, plots:bool):
    file_size = np.array(file_size).reshape(-1, 1)
    model = LinearRegression()
    model.fit(file_size, times)
    latency = model.intercept_
    bandwidth = model.coef_[0]
    print(f"bandwidth = {bandwidth}\nlatency = {latency}")
    print(f"{latency}+filesize * {bandwidth}")
    
    if plots:
        predictions = model.predict(np.array(file_size).reshape(-1, 1))
        plt.scatter(file_size, times, label='Actual Data')
        plt.plot(file_size, predictions, color='red', label='Linear Regression Line')
        plt.xlabel('file size')
        plt.ylabel('times')
        plt.title(title)
        plt.xscale('log')
        plt.legend()
        plt.show()
    return latency, bandwidth

mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="sqlpass",
  database="bandwidth_results"
)
provider = ["aws", "gcp"]
memory = [128, 256, 512, 1024, 2048]

mycursor = mydb.cursor()
mycursor2 = mydb.cursor()

plots = False
response = input("Do you want to see the plots? yes/no\n")
if response == "yes":
    plots = True

for prov in provider:
    for mem in memory:
        for src_des in provider:
            for same_region in ["True", "False"]:
                title = f"provider: {prov}- memory: {mem} - src_des: {src_des} - same_region: {same_region}"
                print(title)
                mycursor.execute(f"SELECT * FROM bandwidth_results.averages\nwhere func_provider = '{prov}' and func_mem={mem} and src_provider='{src_des}' and dest_provider = '{src_des}' and same_region = '{same_region}';")
                myresult = mycursor.fetchall()
                plot_data = []
                for result in myresult:
                    plot_data.append([result[3], result[7], result[8]])

                #sort plot data
                plot_data = sorted(plot_data, key=lambda x: x[0])
                file_size = []
                upload = []
                download = []
                for data_point in plot_data:
                    file_size.append(data_point[0])
                    upload.append(data_point[1])
                    download.append(data_point[2])
                if upload == []:
                    print("no data")
                    continue
                latency, bandwidth = linreg(file_size, upload, title, plots)
                where = f"where func_provider = '{prov}' and func_mem={mem} and src_provider='{src_des}' and dest_provider = '{src_des}' and same_region = '{same_region}';"
                mycursor.execute(f"UPDATE bandwidth_results.linreg SET latency_up = {latency}, bandwidth_up = {bandwidth} {where}")
                latency, bandwidth = linreg(file_size, download, title, plots)
                mycursor.execute(f"UPDATE bandwidth_results.linreg SET latency_down = {latency}, bandwidth_down = {bandwidth} {where}")
                mydb.commit()            


