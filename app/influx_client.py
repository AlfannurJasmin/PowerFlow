"""
PowerFlow - InfluxDB writer
"""

import os
from datetime import datetime, timezone

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

STATE_CODES = {"IDLE": 0, "RUNNING": 1, "STOPPED": 2, "FAULT": 3}


class InfluxWriter:
    def __init__(self):
        self.url = os.environ.get("INFLUX_URL", "http://localhost:8086")
        self.token = os.environ.get("INFLUX_TOKEN", "powerflow-super-secret-token-2026")
        self.org = os.environ.get("INFLUX_ORG", "powerflow-org")
        self.bucket = os.environ.get("INFLUX_BUCKET", "powerflow")
        self.client = None
        self.write_api = None
        self.connected = False
        self._connect()

    def _connect(self):
        try:
            self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org, timeout=3000)
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.connected = True
        except Exception as exc:
            print(f"[InfluxWriter] Could not connect to InfluxDB: {exc}")
            self.connected = False

    def write_snapshot(self, snapshot: dict) -> bool:
        if not self.connected:
            self._connect()
            if not self.connected:
                return False
        try:
            point = (
                Point("production")
                .tag("line", "powerflow")
                .field("products_produced", int(snapshot["products_produced"]))
                .field("defective_products", int(snapshot["defective_products"]))
                .field("current_state", snapshot["state"])
                .field("state_code", STATE_CODES.get(snapshot["state"], -1))
                .time(datetime.now(timezone.utc), WritePrecision.NS)
            )
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            return True
        except Exception as exc:
            print(f"[InfluxWriter] Write failed: {exc}")
            self.connected = False
            return False

    def close(self):
        if self.client:
            self.client.close()