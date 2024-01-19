import subprocess
import sys

#NOTE maybe only call and have check=True
#NOTE shell True probably does not work across platforms
def execute(command:str):
    subprocess.check_call(command, shell=True, stdout=sys.stdout, stderr=subprocess.STDOUT)