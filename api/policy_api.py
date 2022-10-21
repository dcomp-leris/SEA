from flask import Flask, url_for, request
from flask_request_params import bind_request_params
import policy
from policyInterpreter import policyInterpreter
import json
import yaml

app = Flask(__name__)
policies = list()


@app.route('/')
def default_options():
    return 'Welcome to Policy Administrator CNS-OrMM!'


@app.route('/createPolicy', methods=['POST'])
def create_policy():
    global policies
    load_pol()
    json_content = json.dumps(yaml.safe_load(request.data.decode('utf-8')))
    json_content = json.loads(json_content)
    slice_id = json_content["slices"]["slice"]["slice-id"]
    db_credentials = json_content["slices"]["slice"]["database-credentials"]
    print(db_credentials)
    pol = policyInterpreter.create_policies(json_content, db_credentials)
    #policies = pol
    save_pol(pol)
    #print(policies)

    return "OK"


@app.route('/getPolicy', methods=['GET'])
def get_policy():
    global policies
    load_pol()
    p_id = request.data.decode('utf-8')
    #print(p_id)
    #print("Policies", policies)
    for pol in policies:
        if pol["p_id"] == p_id:
            return pol
    return "Policy not found!"


@app.route('/setPolicy', methods=['POST'])
def set_policy():
    global policies
    load_pol()
    p_id = request.data.decode('utf-8')
    #print(p_id)
    for pol in policies:
        if pol["p_id"] == p_id:
            pol["status"] = "blocked"
            save_pol(policies)
            msg= "Policy %s was blocked succesfully" % pol["p_id"]
            return msg
    return "Error to set the policy status to blocked"


def save_pol(pol):
    global policies
    print(policies)
    with open("global_pol.json", "w+") as pol_file:
        json.dump(pol, pol_file)
    pol_file.close()


def load_pol():
    global policies
    #with open("/home/debeltrami/CNS-OrMM/global_pol.json", "r") as pol_file:
    #cns_file = open("global_pol2.json", "a+")
    try:
        pol_file = open("global_pol.json", "r")
        policies = json.load(pol_file)
        #print("pol file %s" % pol_file.readline())
        #print("POL %s" % policies)
        pol_file.close()
    except json.decoder.JSONDecodeError:
        pass


@app.route('/deletePolicy', methods=['POST'])
def deletePolicy():
    data = request.data.decode('utf-8')
    json_content = json.loads(data)


@app.route('/listPolicies', methods=['GET'])
def listPolicies():
    global policies
    load_pol()
    return str(policies)


@app.route('/updatePolicy', methods=['POST'])
def updatePolicy():
    data = request.data.decode('utf-8')
    json_content = json.loads(data)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='1012')
