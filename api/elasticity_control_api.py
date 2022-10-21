from flask import Flask, url_for, request


app = Flask(__name__)


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


if __name__ == '__main__':
    policies = list()
    app.run(debug=True, host='localhost', port='1111')