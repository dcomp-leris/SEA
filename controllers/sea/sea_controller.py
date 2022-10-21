from flask import Flask, url_for, request
#from flask_request_params import bind_request_params
import yaml
import requests
import docker
import json
import socket
import time
import threading
import os
import datetime
from subprocess import call

app = Flask(__name__)

cnsaom_components = dict()
cnsaom_containers = {
    "aggregator": "sliceaggregator:latest",
    "elasticity_control": "elasticitycontrol:latest",
    "monitoring_api": "adapter_api:latest",
    "kubernetes": "adapter_kubernetes:latest",
    "ssh": "adapter_ssh:latest",
    "docker_swarm": "adapter_dswarm:latest",
    "prometheus": "adapter_prom:latest",
    "netdata": "adapter_netdata:latest",
    "openflow": "adapter_openflow:latest",
}
sp_ip = os.environ.get("SLICE_PROVIDER_IP")
policy_admin = "localhost:1012"

@app.route('/', methods=['POST'])
def hello_world():
    print("HELLO")
    return "OK"


@app.route('/start_components', methods=['POST'])
def start_components():
    cnsaom_data = json.loads(request.data.decode('utf-8'))
    #print(type(cnsaom_data))
    start_fix_components(cnsaom_data)
    start_adapters(cnsaom_data)
    save_dict()

    return cnsaom_components


@app.route("/stop_components", methods=["POST"])
def stop_components():
    global cnsaom_components
    load_dict()
    #print(cnsaom_components)
    json_content = json.loads(request.data.decode("utf-8"))
    threads = list()
    client = docker.from_env()
    #print(cnsaom_components)
    for comp in cnsaom_components[json_content["slice"]["id"]]:
        #print(comp["container_id"])
        thread = threading.Thread(target=stop_adapter,
                                  args=(comp["container_id"],))
        threads.append(thread)
        thread.start()
    for t in threads:
        t.join()
    network = client.networks.get(json_content["slice"]["id"])
    network.remove()
    cnsaom_components.pop(json_content["slice"]["id"])
    save_dict()
    return "OK"


@app.route("/deploy_service", methods=["POST"])
def deploy_service():
    global cnsaom_components
    load_dict()
    #print(cnsaom_components)
    threads = list()
    json_content = json.loads(request.data.decode("utf-8"))
    for sp in json_content["slice"]["slice-parts"]:
        for comp in cnsaom_components[json_content["slice"]["id"]]:
            if comp.get("type")  == "man_adapter" and comp.get("sp_id") == sp["sp-id"]:
                thread = threading.Thread(target=adapter_deploy_service,
                                          args=(comp, sp))
                threads.append(thread)
                thread.start()
    for t in threads:
        t.join()

    return "Service has been deployed successfully!"


@app.route("/scale_in", methods=["POST"])
def scale_in():
    global cnsaom_components
    load_dict()
    cnsaom_data = json.loads(request.data.decode("utf-8"))
    #print(cnsaom_data)
    threads = list()
    slice_data = cnsaom_data["slice"]
    for sp in slice_data["slice-parts"]:
        for comp in cnsaom_components[slice_data["id"]]:
            #print("COMP SCALE IN:", comp)
            if comp["type"] in ["man_adapter", "mon_adapter"]:
                if comp["sp_id"] == sp["sp-id"]:
                    print(comp["container_id"])
                    thread = threading.Thread(target=stop_adapter,
                                              args=(comp["container_id"],))
                    threads.append(thread)
                    thread.start()
                    cnsaom_components[slice_data["id"]].remove(comp)
    for t in threads:
        t.join()

    save_dict()
    return "Scale-In performed successfully!"


@app.route("/scale_out", methods=["POST"])
def scale_out():
    global cnsaom_components
    load_dict()
    cnsaom_data = json.loads(request.data.decode("utf-8"))
    for comp in cnsaom_components[cnsaom_data["slice"]["id"]]:
        if comp["type"] == "database":
            cnsaom_data["slice"]["docker-network"] = comp["container_net"]
    #print(cnsaom_data)
    start_adapters(cnsaom_data)
    save_dict()

    return "Scale-out performed successfully!"


@app.route("/scale_down", methods=["POST"])
def scale_down():
    global cnsaom_components
    load_dict()
    pol_id = request.data.decode("utf-8")
    pol = requests.get(f'http://{policy_admin}/getPolicy',
                       data=pol_id)
    pol_data = json.loads(pol.content)
    #print("Policy:", pol_data)
    for comp in cnsaom_components[pol_data["slice_id"]]:
        if comp["type"] == "man_adapter":
            if comp["sp_id"] in pol_data["sp_id"] and comp["vim"] == "ssh":
                commands = pol_data["action"]["commands"]
                #print("Commands to be triggered:", commands)
                response = requests.post(
                   f"http://localhost:" + str(comp["container_port"]) +
                   "/v-elasticity", json={
                        "vim_ip": comp["vwim_ip"],
                        "vim_port": comp["vwim_port"],
                        "username": comp["username"],
                        "password": comp["password"],
                        "commands": commands})
                print("V-elasticity response:", response.content)
            elif comp["sp_id"] in pol_data["sp_id"] and comp["vim"] == "kubernetes":
                replicas = pol_data["action"][0]["replicas"]
                print("Replicas to be added:", replicas)
                response = requests.post(
                   f"http://localhost:" + str(comp["container_port"]) +
                   "/v-elasticity", json={
                        "vim_ip": comp["vwim_ip"],
                        "vim_port": comp["vwim_port"],
                        "username": comp["username"],
                        "password": comp["password"],
                        "token": pol_data["action"][0]["token"],
                        "replicas": replicas})
                print("V-elasticity response:", response.content)
            elif (comp["sp_id"] in pol_data["sp_id"]
                    and comp["vwim"] == "openflow"
                    and pol_data["elasticity-type"] == "scale-down-queue"):
                response = requests.post(
                    f"http://localhost:" + str(comp["container_port"]) +
                    "/v-elasticity-queue-down", json={
                        "wim_ip": comp["vwim_ip"],
                        "wim_port": comp["vwim_port"],
                        "username": comp["username"],
                        "password": comp["password"],
                        "ssh_port": comp["ssh_port"],
                        "commands": pol_data["action"][0]["commands"],
                        "flows": pol_data["action"][0]["flows"],
                    })
                print("V-elasticity-queue-down response:", response.content)
            elif (comp["sp_id"] in pol_data["sp_id"]
                    and comp["vwim"] == "openflow"
                    and pol_data["elasticity-type"] == "scale-down-link"):
                response = requests.post(
                    f"http://localhost:" + str(comp["container_port"]) +
                    "/v-elasticity-link-down", json={
                        "wim_ip": comp["vwim_ip"],
                        "wim_port": comp["vwim_port"],
                        "username": comp["username"],
                        "password": comp["password"],
                        "ssh_port": comp["ssh_port"],
                        "commands": pol_data["action"][0]["commands"],
                        "flows": pol_data["action"][0]["flows"],
                    })
                print("V-elasticity-link-down response:", response.content)

    pol = requests.post(f'http://{policy_admin}/setPolicy',
                        data=pol_id)
    return "Scale-down performed successfully!"


@app.route("/scale_up", methods=["POST"])
def scale_up():
    global cnsaom_components
    load_dict()
    pol_id = request.data.decode("utf-8")
    #print("ANDRER POL %s" % policy_admin)
    pol = requests.get(f"http://{policy_admin}/getPolicy",
                       data=pol_id)
    #print("DEBUG pol %s" % pol.content) 
    pol_data = json.loads(pol.content)
    if pol_data["status"] == "blocked":
        msg = "This policy already triggered an elasticity operation."
        #print(msg)
        return msg
    #print("Policy:", pol_data)
    for comp in cnsaom_components[pol_data["slice_id"]]:
        if comp["type"] == "man_adapter":
            if comp["sp_id"] in pol_data["sp_id"] and comp["vwim"] == "ssh":
                commands = pol_data["action"]["commands"]
                #print("Commands to be triggered:", commands)
                response = requests.post(
                   "http://localhost:" + str(comp["container_port"]) +
                   "/v-elasticity", json={
                        "vim_ip": comp["vim_ip"],
                        "vim_port": comp["vim_port"],
                        "username": comp["username"],
                        "password": comp["password"],
                        "commands": commands})
                print("Vertical elasticity response:", response.content)
            elif comp["sp_id"] in pol_data["sp_id"] and comp["vwim"] == "kubernetes":
                replicas = pol_data["action"][0]["replicas"]
                print("Replicas to be added:", replicas)
                response = requests.post(
                   f"http://localhost:" + str(comp["container_port"]) +
                   "/v-elasticity", json={
                        "vim_ip": comp["vim_ip"],
                        "vim_port": comp["vim_port"],
                        "username": comp["username"],
                        "password": comp["password"],
                        "token": pol_data["action"][0]["token"],
                        "replicas": replicas})
                print("V-elasticity response:", response.content)
            elif (comp["sp_id"] in pol_data["sp_id"]
                    and comp["vwim"] == "openflow"
                    and pol_data["elasticity-type"] == "scale-up-queue"):
                response = requests.post(
                    f"http://localhost:" + str(comp["container_port"]) +
                    "/v-elasticity-queue-up", json={
                        "wim_ip": comp["vwim_ip"],
                        "wim_port": comp["vwim_port"],
                        "username": comp["username"],
                        "password": comp["password"],
                        "ssh_port": comp["ssh_port"],
                        "commands": pol_data["action"].get("commands"),
                        "flows": pol_data["action"].get("flows"),
                    })
                print("V-elasticity-queue-up response:", response.content)
            elif (comp["sp_id"] in pol_data["sp_id"]
                    and comp["vwim"] == "openflow"
                    and pol_data["elasticity-type"] == "scale-up-link"):
                response = requests.post(
                    f"http://localhost:" + str(comp["container_port"]) +
                    "/v-elasticity-link-up", json={
                        "wim_ip": comp["vwim_ip"],
                        "wim_port": comp["vwim_port"],
                        "username": comp["username"],
                        "password": comp["password"],
                        "ssh_port": comp["ssh_port"],
                        "commands": pol_data["action"].get("commands"),
                        "flows": pol_data["action"].get("flows"),
                    })
                print("V-elasticity-link-up response:", response.content)

    pol = requests.post(f'http://{policy_admin}/setPolicy',
                        data=pol_id)
    print("Scale up, finished at: %s" % datetime.datetime.now())
    
    return "Scale-up performed successfully!"


def stop_adapter(container_id):
    client = docker.from_env()
    container = client.containers.get(container_id)
    container.stop()
    container.remove()

    return "Containers stopped and deleted."


def start_adapters(cnsaom_data):
    global cnsaom_components
    slice_data = cnsaom_data["slice"]
    threads = list()
    slice_id = slice_data["id"]
    for sp in slice_data["slice-parts"]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('localhost', 0))
        port = s.getsockname()[1]
        s.close()

        thread = threading.Thread(target=create_adapter,
                                  args=(slice_id, port, "management",
                                        sp, slice_data["docker-network"]))
        threads.append(thread)
        thread.start()

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('localhost', 0))
        port = s.getsockname()[1]
        s.close()
        #print(cnsaom_components[slice_id])
        db_container = [comp for comp in cnsaom_components[slice_id] if comp["type"] == "database"]
        db_param = None
        #print("db CONTAINER", db_container)
        slice_data["db-parameters"]["db-port"] = db_container[0]["container_port"]
        slice_data["db-parameters"]["db-user"] = db_container[0]["username"]
        db_param = slice_data["db-parameters"] 
        thread = threading.Thread(target=create_adapter,
                                  args=(slice_id, port, "monitoring",
                                        sp, slice_data["docker-network"],
                                        db_param))
        threads.append(thread)
        thread.start()

    for t in threads:
        t.join()

    return "Adapters were started."


def create_adapter(slice_id, port, adapter_type, sp_data, dock_net, db=None):
    client = docker.from_env()
    man_parameters = sp_data["management-parameters"]
    vim_adapter = True if man_parameters.get("vim") else False
    if adapter_type == "management":
        user = man_parameters.get("user")
        passwd = man_parameters.get("password")
        ssh_port = man_parameters.get("ssh-port")
        sp_id = sp_data["sp-id"]
        vwim_ip = man_parameters["ip"]
        vwim_port = man_parameters["port"]
        vwim = man_parameters.get("vim") if vim_adapter else man_parameters.get("wim")
        container_name = sp_id + "-" + vwim

        container = client.containers.run(
                              cnsaom_containers[vwim],
                              detach=True, name=container_name,
                              network=dock_net,
                              ports={'1010/tcp': ('localhost', port)})
        #print(str(port))
        #print(man_parameters)
        while True:
            try:
                output = requests.post(
                    "http://localhost:" + str(port) + "/set_config",
                    json=man_parameters)
                #print(output)
                #print(output.content)
                break
            except requests.exceptions.ConnectionError:
                pass
        cnsaom_components[slice_id].append({
            "container_name": container_name,
            "container_id": container.id,
            "container_port": port,
            "type": "man_adapter",
            "vwim": vwim,
            "sp_id": sp_id,
            "vwim_ip": vwim_ip,
            "vwim_port": vwim_port,
            "ssh_port": ssh_port,
            "username": user,
            "password": passwd
        })

    elif adapter_type == "monitoring":
        mon_parameters = sp_data["monitoring-parameters"]
        mon_parameters["db-parameters"] = db
        tool = mon_parameters["tool"]
        tool_ip = mon_parameters["tool-ip"]
        tool_port = mon_parameters["tool-port"]
        granularity = mon_parameters["granularity-secs"]
        metrics = mon_parameters["metrics"]
        sp_id = sp_data["sp-id"]
        container_name = sp_data["sp-id"] + tool
        mon_parameters["sp-id"] = sp_id
        mon_parameters["slice-id"] = slice_id
        mon_parameters["mon-port-enabled"] = mon_parameters.get("mon-port-enabled")
        container = client.containers.run(
            cnsaom_containers["monitoring_api"],
            detach=True, name=container_name,
            network=dock_net, tty=True,
            ports={'1010/tcp': ('localhost', port)})
        while True:
            try:
                requests.post("http://localhost:" + str(port) +
                              "/start_monitoring",
                              json=mon_parameters)
                break
            except requests.exceptions.ConnectionError:
                pass
        #print(str(port))
        #print(mon_parameters)
        command = f'bash -c "python3 CNS-OrMM/monitoring/monAdapters/adapter_{tool}.py"'
        output = container.exec_run(command, detach=True, tty=True)
        #print(output)

        cnsaom_components[slice_id].append({
            "container_name": container_name,
            "container_id": container.id,
            "container_port": port,
            "type": "mon_adapter",
            "tool": tool,
            "sp_id": sp_id,
            "tool_ip": tool_ip,
            "tool_port": tool_port,
            "granularity": granularity,
            "metrics": metrics,
            "mon_port_enabled": mon_parameters["mon-port-enabled"],
        })


def start_fix_components(cnsaom_data):
    # This method will start the Slice Aggregator container, RabbitMQ
    # container, Database container, Elasticity Control container
    ports = list()
    slice_data = cnsaom_data["slice"]
    slice_id = slice_data["id"]
    for i in range(0, 4):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('localhost', 0))
        ports.append(s.getsockname()[1])
        s.close()
    #print("PORTS: ", ports)

    client = docker.from_env()
    container_name = slice_id + "_monitoring_database"
    db_param = slice_data["db-parameters"]

    container = client.containers.run(
        slice_data["db-parameters"]["db"],
        detach=True, name=container_name,
        network=slice_data["docker-network"],
        #ports={'8086/tcp': ('localhost', ports[0])},
        ports={'8086/tcp': ('localhost', 20000)},
        environment={'DOCKER_INFLUXDB_INIT_MODE': 'setup',
                     'DOCKER_INFLUXDB_INIT_USERNAME': db_param["user"],
                     'DOCKER_INFLUXDB_INIT_PASSWORD': db_param["password"],
                     'DOCKER_INFLUXDB_INIT_ORG': db_param["org-name"],
                     'DOCKER_INFLUXDB_INIT_BUCKET': db_param["bucket-name"],
                     'DOCKER_INFLUXDB_INIT_RETENTION': 0,
                     'DOCKER_INFLUXDB_INIT_ADMIN_TOKEN': db_param["token"],
                     'INFLUXDB_HTTP_ENABLED': "true",
                     'INFLUXDB_BIND_ADDRESS': ':8086',
                     'INFLUXDB_HTTP_AUTH_ENABLED': "true"},
        )

    print("The Database", container_name, "has started!")
    cnsaom_components[slice_id] = [{
       "container_name": container_name,
       "container_id": container.id,
       "container_port": 20000,
       "type": "database",
       "db-ip": db_param["db-ip"],
       "username": db_param["user"],
       "password": db_param["password"],
       "org-name": db_param["org-name"],
       "bucket-name": db_param["bucket-name"],
       "token": db_param["token"],
       "container_net": slice_data["docker-network"]}]


def adapter_deploy_service(comp, sp):
    while True:
        try:
            response = requests.post("http://localhost:" +
                                     str(comp["container_port"]) +
                                     "/deploy_service",
                                     json={"vim_ip": comp["vwim_ip"],
                                           "vim_port": comp["vwim_port"],
                                           "username": comp["username"],
                                           "password": comp["password"],
                                           "sp": sp})
            print("Deploy service response:", response.content)
            break
        except requests.exceptions.ConnectionError:
            pass
    return "OK"


def save_dict():
    # filename = ""
    global cnsaom_components
    write_file = open("global_dict.json", 'w')
    json.dump(cnsaom_components, write_file)
    write_file.close()


def load_dict():
    global cnsaom_components
    with open("global_dict.json", "r") as cns_file:
        cns_file = open("global_dict.json", "r")
        cnsaom_components = json.load(cns_file)
        #print(cnsaom_components)
        #print(type(cnsaom_components))
    cns_file.close()


if __name__ == '__main__':
#    sp_ip = os.environ.get("SLICE_PROVIDER_IP")
#    policy_admin = f"${sp_ip}:1012"
    app.run(debug=True, host='localhost', port='5001')


