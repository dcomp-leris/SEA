# encoding: utf-8

from imp import init_builtin
import sys
import time
import requests
import json
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import ASYNCHRONOUS
from datetime import timedelta, datetime


class adapterOpenflow():
    metrics_mapping = {
        "PACKETS_RX": "rx_packets",
        "PACKETS_TX": "tx_packets",
        "BYTES_RX": "rx_bytes",
        "BYTES_TX": "tx_bytes",
        "DROPS_TX": "tx_dropped",
        "DROPS_RX": "rx_dropped",
        "ERRORS_RX": "rx_errors",
        "ERRORS_TX": "tx_errors",
        "FRAME_ERRORS_RX": "rx_frame_err",
        "OVERRUN_ERRORS_RX": "rx_over_err",
        "CRC_ERRORS_RX": "rx_crc_err",
        "COLLISIONS": "collisions",
    }

    def __init__(self, initial_config):
        self.slice_id = initial_config['slice-id']
        self.slice_part_id = initial_config['sp-id']
        self.monitoring_tool = initial_config['tool']
        self.monitoring_ip = initial_config['tool-ip']
        self.monitoring_port = initial_config['tool-port']
        self.interval = initial_config['granularity-secs']
        self.mon_port_enabled = initial_config['mon-port-enabled']
        self.metrics = initial_config['metrics']
        self.db = initial_config["db-parameters"]

    def get_metrics(self):
        url = f"http://{self.monitoring_ip}:{self.monitoring_port}/"
        statement = "stats/switches"
        request = requests.get(url=url+statement)
        output = json.loads(request.text)
        message = []
        print("Output:", output)
        if self.mon_port_enabled:
            for sw in output:
                statement = f"stats/port/{sw}"
                request = requests.get(url=url+statement)
                output_data = json.loads(request.text)
                for port in output_data.get(str(sw)):
                    if port['port_no'] != 'LOCAL':
                        for metric in self.metrics:
                            measurement = metric
                            if metric not in ['FRAME_ERRORS_RX', 'OVERRUN_ERRORS_RX', 'CRC_ERRORS_RX', 'COLLISIONS']:
                                value = port.get(self.metrics_mapping.get(metric))
                            else:
                                value = port['properties'][0].get(self.metrics_mapping.get(metric))
                            ts = datetime.now().timestamp()
                            message.append({'measurement': measurement,
                                            'tags': {
                                                'datapath_id': sw,
                                                'port_id': port['port_no'],
                                                'resource_type': 'Physical switch',
                                                'slice_id': self.slice_id,
                                                'slice_part_id': self.slice_part_id},
                                            'time': datetime.fromtimestamp(ts).isoformat(),
                                            'fields': {'value': float(value)} 
                                            })
        return message

    def add_metrics(self, metrics):
        url = "http://"+self.db["db-ip"]+":"+str(self.db["db-port"])
        client = InfluxDBClient(url=url,
                                token=self.db["token"],
                                org=self.db["org-name"])
        write_api = client.write_api(write_options=ASYNCHRONOUS)
        print("BEFORE", metrics)
        metrics = json.dumps(metrics)
        metrics = metrics.replace("\'","\"")
        metrics = json.loads(metrics)
        print("AFTER", metrics)
        write_api.write(bucket=self.db["bucket-name"], org=self.db["org-name"], record=metrics)


with open("mon_param.json", "r") as file:
    mon_param = json.load(file)
print(mon_param)
#initial_config.update(update)
#print(initial_config)
adapterOpenflow = adapterOpenflow(mon_param)

while True:
    metrics = adapterOpenflow.get_metrics()
    adapterOpenflow.add_metrics(metrics)
    #publisher = monAdapters.monAdaptersPublisher(json.dumps(initial_config, separators=(',', ':')))
    #publisher.connection(message)
    time.sleep(int(adapterOpenflow.interval))
