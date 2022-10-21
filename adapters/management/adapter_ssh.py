from flask import Flask, url_for, request
from flask_request_params import bind_request_params
import yaml
import requests
import docker
import json
import paramiko
import time

app = Flask(__name__)


@app.route('/set_config', methods=['POST'])
def set_config():
    man_data = request.json
    man_param["ssh_ip"] = man_data["ip"]
    man_param["ssh_port"] = man_data["port"]
    man_param["ssh_user"] = man_data["user"]
    man_param["ssh_pass"] = man_data["password"]

    return 'OK'


@app.route('/show', methods=['GET'])
def show():
    print(man_param)
    return man_param


@app.route('/')
def default_options():
    return 'Welcome to the SSH adapter of Resource and VM Management'


@app.route('/deploy_service', methods=['POST'])
def deploy_service():
    params = json.loads(request.data.decode("utf-8"))
    print("Check the man_param: ", params)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=params["vim_ip"], port=params["vim_port"],
                username=params["username"], password=params["password"])
    for command in params["sp"]["commands"]:
        print(command)
        stdin, stdout, stderr = ssh.exec_command(command)  # Non-blocking call
        exit_status = stdout.channel.recv_exit_status()  # Blocking call
        if exit_status == 0:
            print("Command Ok!")
        else:
            print("Error", exit_status)
    ssh.close()

    return "Commands executed properly!"


@app.route("/v-elasticity", methods=["POST"])
def v_elastictiy():
    params = json.loads(request.data.decode("utf-8"))
    print("Check the man_param: ", params)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=params["vim_ip"], port=params["vim_port"],
                username=params["username"], password=params["password"])
    for command in params["commands"]:
        print(command)
        stdin, stdout, stderr = ssh.exec_command(command)  # Non-blocking call
        exit_status = stdout.channel.recv_exit_status()  # Blocking call
        if exit_status == 0:
            print("Command Ok!")
        else:
            print("Error", exit_status)
    ssh.close()

    return "Commands executed properly!"


@app.route('/getService', methods=['POST'])
def get_service():
    return "OK"


@app.route('/deleteService', methods=['POST'])
def delete_service():
    return "OK"


if __name__ == '__main__':
    man_param = dict()
    app.run(debug=True, host='0.0.0.0', port='1010')


