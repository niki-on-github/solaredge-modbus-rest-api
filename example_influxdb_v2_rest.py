#!/usr/bin/env python3

from influxdb_client import InfluxDBClient
import os
from flask import Flask, jsonify, request

app = Flask(__name__)

def fetch_tables():
    INFLUXDB_URL = os.environ.get("INFLUXDB_URL")
    INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN")
    INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG")
    INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET")

    client = InfluxDBClient(
        url=INFLUXDB_URL, 
        token=INFLUXDB_TOKEN, 
        org=INFLUXDB_ORG
    )
    query_api = client.query_api()

    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: 0)
      |> last()
      |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
    '''

    result = {}
    tables = query_api.query(query)

    for table in tables:
        for record in table.records:
            measurement = record.values['_measurement']
            
            if measurement not in result:
                result[measurement] = {}
                
            result[measurement] = {
                "time": record.values['_time'].isoformat(),
                "fields": {k: v for k, v in record.values.items() if not k.startswith(('_', 'tag_'))}
            }

    client.close()
    return result

@app.route('/', methods=['GET'])
def get_values():
    return jsonify(fetch_tables())

@app.route('/surplus', methods=['GET'])
def get_surplus():
    capacity = float(request.args.get('capacity', "0"))
    values = fetch_tables()

    export = values["meter"]["fields"]["power"]
    if export - capacity < 20:
        return {
            "surplus": False,
            "reason": f"No overcapacity (export={export}, required capacity={capacity})"
        }

    battery = values["battery"]["fields"]["soe"]
    if battery < 98:
        return {
            "surplus": False,
            "reason": f"Battery is not Full (battery={battery}%)"
        }

    return { "surplus": True }

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
