import json
import tkinter as tk

class main(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("testOps")
        self.geometry("500x500")

        self.main_frame = tk.Frame(self)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.columnconfigure(2, weight=1)

        self.build_button = tk.Button(self.main_frame, text = "build", command=self.show_frame)
        self.build_button.grid(row=0, column=0, sticky='WE')
        self.deploy_button = tk.Button(self.main_frame, text = "deploy", command=self.deploy)
        self.deploy_button.grid(row=0, column=1, sticky='WE')
        self.analyse_button = tk.Button(self.main_frame, text = "analyse", command=self.analyse)
        self.analyse_button.grid(row=0, column=2, sticky='WE')

        self.main_frame.pack(fill='x')

        self.build_form_instance = build_form(self)
    
    def show_frame(self):
        self.main_frame.pack_forget()
        self.build_form_instance.pack(fill='x')
    
    def show_main_frame(self, forget):
        self.main_frame.pack(fill='x')
        

    def deploy(self):
        print("deploy")

    def analyse(self):
        print("analyze")

class build_form(tk.Frame):    
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.to_main_frame = tk.Button(self, text = "back", command = self.back)
        self.to_main_frame.grid(row=0, column=0)

        self.project_path_label = tk.Label(self, text="Project Path:")
        self.project_path_label.grid(row=1, column=0, sticky="w")
        self.project_path = tk.Entry(self)
        self.project_path.grid(row=1, column=1)

        self.main_class_label = tk.Label(self, text="Main Class:")
        self.main_class_label.grid(row=2, column=0, sticky="w")
        self.main_class = tk.Entry(self)
        self.main_class.grid(row=2, column=1)

        self.function_name_label = tk.Label(self, text="Function Name:")
        self.function_name_label.grid(row=3, column=0, sticky="w")
        self.function_name = tk.Entry(self)
        self.function_name.grid(row=3, column=1)

        self.providers = tk.Label(self, text="Providers")
        self.providers.grid(row=4, column=0)

        self.aws_var = tk.IntVar()
        self.gcp_var = tk.IntVar()

        self.aws = tk.Checkbutton(self, text="AWS", variable=self.aws_var)  # Use grid manager for Checkbutton
        self.aws.grid(row=5, column=0)
        self.gcp = tk.Checkbutton(self, text="GCP", variable=self.gcp_var)  # Use grid manager for Checkbutton
        self.gcp.grid(row=6, column=0)

        self.build = tk.Button(self, text = "build", command = self.build)
        self.build.grid(row=7, column=0)

    def back(self):
        self.pack_forget()
        self.parent.main_frame.pack(fill='x')
    
    def build(self):
        build_dict:dict= {}
        #create json
        build_dict["project_path"] = self.project_path.get()
        build_dict["main_class"] = self.main_class.get()
        build_dict["function_name"] = self.function_name.get()
        providers = []
        if self.aws_var.get():
            providers.append('aws')
        if self.gcp_var.get():
            providers.append('gcp')
        if not providers == []:
            build_dict["provider"]=providers

        f = open("build.json", 'w')
        f.write(json.dumps(build_dict, indent=4))
        #call build using that json


if __name__ == "__main__":
    app = main()
    app.mainloop()


