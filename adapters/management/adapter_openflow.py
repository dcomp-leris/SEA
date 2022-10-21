from flask import Flask, url_for, request
from flask_request_params import bind_request_params
import yaml
import requests
import docker
import json
import paramiko
import time
from pprint import pprint

app = Flask(__name__)


@app.route('/set_config', methods=['POST'])
def set_config():
    man_data = request.json
    man_param["wim_ip"] = man_data["ip"]
    man_param["wim_port"] = man_data["port"]
    man_param["user"] = man_data["user"]
    man_param["password"] = man_data["password"]
    man_param["ssh_port"] = man_data["ssh-port"]

    return 'OK'


@app.route('/show', methods=['GET'])
def show():
    print(man_param)
    return man_param


@app.route('/')
def default_options():
    return 'Welcome to the Openflow WIM adapter of Resource and VM Management'


@app.route("/v-elasticity-queue-up", methods=["POST"])
def v_elastictiy_queue_up():
    params = json.loads(request.data.decode("utf-8"))
    print("Check the parameters: ", params)

    # A ssh using paramiko was necessary to setup the queues
    # using ovs-vsctl commands
    exec_shell(params.get("commands"))
    flows = params.get("flows")
    # After that a new flow need to be added using OF controller API
    #for flow in flows:
    #    add_flow_rule(flows)

    return "Queues and Flows were configured!"

@app.route("/v-elasticity-queue-down", methods=["POST"])
def v_elastictiy_queue_down():
    params = json.loads(request.data.decode("utf-8"))
    print("Check the parameters: ", params)

    # A ssh using paramiko was necessary to delete the queues
    # using ovs-vsctl commands
    exec_shell(params.get("commands"))

    # After that a previous flow need to be removed using OF
    # controller API
    flows = params.get("flows")
    delete_flows_rules(flows)

    return "Queues and Flows were removed!"

@app.route("/v-elasticity-link-up", methods=["POST"])
def v_elastictiy_link_up():
    params = json.loads(request.data.decode("utf-8"))
    print("Check the parameters: ", params)

    # A ssh using paramiko was necessary to setup the queues
    # using ovs-vsctl commands
    exec_shell(params.get("commands"))
    flows = params.get("flows")
    # After that a new flow need to be added using OF controller API
    #for flow in flows:
    #    add_flows_rule(flows)

    return "Virtual Links and Switches were added!"


@app.route("/v-elasticity-link-down", methods=["POST"])
def v_elastictiy_link_down():
    params = json.loads(request.data.decode("utf-8"))
    print("Check the parameters: ", params)

    exec_shell(params.get("commands"))

    # After that a new flow need to be added using OF controller API
    flows = params.get("flows")
    delete_flows_rules(flows)

    return "Virtual links were deleted!"


@app.route("/list-dpids", methods=["GET"])
def list_dpids():
    url = f"{man_param['wim-ip']}:{man_param['wim-port']}/stats/switches"
    response = requests.get(url)
    print(response)

    return response


@app.route("/list-flows-per-dpid", methods=["GET"])
def list_flows_per_dpid():
    params = json.loads(request.data.decode("utf-8"))
    dpids = params.get("dpids")
    response = list()

    for dpid in dpids:
        url = f"{man_param['wim-ip']}:{man_param['wim-port']}/stats/flow/{dpid}"
        response.append(requests.get(url))
        print(response)

    return response


@app.route("/list-queues", methods=["GET"])
def list_queues():
    params = json.loads(request.data.decode("utf-8"))
    dpids = params.get("dpids")
    response = list()

    for dpid in dpids:
        url = f"{man_param['wim-ip']}:{man_param['wim-port']}/stats/queue/{dpid}"
        response.append(requests.get(url))
        print(response)

    return response

def exec_shell(commands):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=man_param["wim_ip"], port=man_param["ssh_port"],
                username=man_param["user"], password=man_param["password"])
    for command in commands:
        print(command)
        stdin, stdout, stderr = ssh.exec_command(command)
        if command.startswith("sudo"):
            stdin.write(man_param["password"] + "\n")
            stdin.flush()
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("Command executed ok!")
        else:
            print("Error", exit_status)
    ssh.close()


def add_flows_rules(flows):
    for flow in flows:
        url = f"{man_param['wim-ip']}:{man_param['wim-port']}/stats/flowentry/add"
        response.append(requests.post(url, data=flow))
        print(response)

    return response


def delete_flows_rules(flows):
    for flow in flows:
        url = f"{man_param['wim-ip']}:{man_param['wim-port']}/stats/flowentry/delete"
        response.append(requests.post(url, data=flow))
        print(response)

    return response


if __name__ == '__main__':
    man_param = dict()
    app.run(debug=True, host='0.0.0.0', port='1010')


