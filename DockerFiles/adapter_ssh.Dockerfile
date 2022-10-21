FROM ubuntu:focal
RUN \
    apt -y update && \
    apt -y install git python3-pip curl && \
    pip3 install requests && \
    pip3 install pika==0.13.1 && \
    pip3 install influxdb --default-timeout=100 && \
    pip3 install flask --default-timeout=100 && \
    pip3 install flask_request_params --default-timeout=100 && \
    pip3 install pyyaml --default-timeout=100 && \
    pip3 install paramiko --default-timeout=100 && \
    pip3 install docker --default-timeout=100 && \
    git clone %the sea project% && \
    cd SEA
ENTRYPOINT python3 SEA/adapters/management/adapter_ssh.py >> adapter.log
