from flask import Flask, url_for, request
import yaml
import requests, logging
import docker
import json

app = Flask(__name__)
adapter_dict = {}
man_controller = "localhost:5001"
mon_controller = "localhost:1112"
orch_controller = "localhost:113"
controller = "localhost:5001"
headers = {'content-type': 'application/json'}


@app.route('/createCNSComponents', methods=['POST'])
def create_cns_components():
    json_content = json.dumps(yaml.safe_load(request.data.decode('utf-8')))
    json_content = json.loads(json_content)
    print(json_content)
    # We need to create private networks between the containers in order to
    # ensure the isolation and communication between them
    client = docker.from_env()
    print(json_content)
    slice_id = json_content["slice"]["id"]

    net_info = create_docker_net(client, slice_id)
    json_content["slice"]["docker-network"] = net_info.short_id
    print(net_info.short_id)
    cnsamo = create_containers(json_content)

    return "OK"


@app.route("/stopCNSComponents", methods=["POST"])
def stop_cns_components():
    json_content = json.dumps(yaml.safe_load(request.data.decode('utf-8')))
    json_content = json.loads(json_content)
    r = requests.post(f'http://{controller}/stop_components',
                      data=json.dumps(json_content), headers=headers)
    return "The CNS Components were stopped."


@app.route("/deploy_service", methods=["POST"])
def deploy_service():
    json_content = json.dumps(yaml.safe_load(request.data.decode('utf-8')))
    json_content = json.loads(json_content)
    r = requests.post(f"http://{controller}/deploy_service",
                      data=json.dumps(json_content), headers=headers)
    return "The service was deployed succesfully."


@app.route("/scale_out", methods=["POST"])
def horizontal_scale_out():
    # Addition of new SPs (1 or more)
    json_content = json.dumps(yaml.safe_load(request.data.decode('utf-8')))
    json_content = json.loads(json_content)
    print(json_content)
    r = requests.post(f'http://{controller}/scale_out',
                      data=json.dumps(json_content), headers=headers)
    print(r)

    return "Horizontal Scale-Out performed successfully!"


@app.route("/scale_in", methods=["POST"])
def horizontal_scale_in():
    # Removal of SPs (1 or more)
    json_content = json.dumps(yaml.safe_load(request.data.decode('utf-8')))
    json_content = json.loads(json_content)
    print(json_content)
    r = requests.post(f'http://{controller}/scale_in',
                      data=json.dumps(json_content), headers=headers)
    print(r)

    return "Horizontal Scale-In performed successfully!"


@app.route("/elasticity/scale-in", methods=["POST"])
def scale_in():
    print(request.data.decode("utf-8"))
    return "Horizontal elasticity Scale-In."


@app.route("/elasticity/scale-out", methods=["POST"])
def scale_out():
    print(request.data.decode("utf-8"))
    return "Horizontal elasticity Scale-Out."


@app.route("/elasticity/scale-down", methods=["POST"])
def scale_down():
    output = json.loads(request.data.decode("utf-8"))
    print(output)
    pol_id = output["_message"]
    print(pol_id)
    pol_data = requests.post(f'http://{controller}/scale_down',
                             data=pol_id)
    return "OK"


@app.route("/elasticity/scale-up", methods=["POST"])
def scale_up():
    output = json.loads(request.data.decode("utf-8"))
    print(output)
    pol_id = output["_message"]
    print(pol_id)
    pol_data = requests.post(f'http://{controller}/scale_up',
                             data=pol_id)
    return "OK"

@app.route("/elasticity/scale-up-queue", methods=["POST"])
def scale_up_queue():
    output = json.loads(request.data.decode("utf-8"))
    print(output)
    pol_id = output["_message"]
    print(pol_id)
    pol_data = requests.post(f'http://{controller}/scale_up',
                             data=pol_id)
    return "OK"

@app.route("/elasticity/scale-up-link", methods=["POST"])
def scale_up_link():
    output = json.loads(request.data.decode("utf-8"))
    print(output)
    pol_id = output["_message"]
    print(pol_id)
    pol_data = requests.post(f'http://{controller}/scale_up',
                             data=pol_id)
    return "OK"


def create_containers(json_content):
    r = requests.post(f'http://{controller}/start_components',
                      data=json.dumps(json_content), headers=headers)
    print(r)

    return r


def create_docker_net(client, slice_id):
    net_name = slice_id
    net_info = client.networks.create(name=slice_id)
    return net_info


def create_man_components(sps_info):
    r = requests.post(f'{man_controller}/start_management',
                      data=json.dumps(sps_info))
    print(r)

    return r


def create_mon_components(sps_info):
    r = requests.post(f'{mon_controller}/start_monitoring', data=sps_info)
    print(r)

    return r


def create_orch_components(sps_info):
    r = requests.post(f'{orch_controller}/start_elasticity_listener', data=sps_info)
    print(r)

    return r


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='1014')
