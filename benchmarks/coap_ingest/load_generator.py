import asyncio
from datetime import datetime
import uuid
from multiprocessing import Process

from aiocoap import *
from cbor2 import dumps

sample_message = [{"asset": "TI sensorTag/luxometer", "sensor_values": {"lux": 65679.604}}]

mixed_message = [{"asset": "TI sensorTag/luxometer", "sensor_values": {"lux": 65679.604}},
                  {"asset": "TI sensorTag/luxometer", "sensor_values": {"lux": 65679.604}},
                  {"asset": "TI sensorTag/pressure", "sensor_values": {"pressure": 900.5}},
                  {"asset": "TI sensorTag/humidity", "sensor_values": {"temperature": 28, "humidity": 23}},
                  {"asset": "TI sensorTag/temperature", "sensor_values": {"ambient": 29, "object": 19}},
                  {"asset": "TI sensorTag/accelerometer", "sensor_values": {"x": 0, "z": 1, "y": 2}},
                  {"asset": "TI sensorTag/gyroscope", "sensor_values": {"x": 230, "z": -240, "y": -88}},
                  {"asset": "TI sensorTag/magnetometer", "sensor_values": {"x": -184, "z": 208, "y": -179}},
                  {"asset": "mouse", "sensor_values": {"button": "up"}}]

#pprint(sample_message)


def generate_samples(n, mixed_samples=False):
    """
    Generates n*8 tuples if mixed_samples is True, generates n tuples
    :param n: number of sets to generate
    :param mixed_samples: Default False, if true generate n*8 sets
    :return: List of payload tuples
    """
    if mixed_samples:
        _message = mixed_message
    else:
        _message = sample_message

    payloads = []

    for _i in _message:
        _i["key"] = next(generate_uuid())
        #print(_i["key"])
        payloads.extend([_i])

    #print(payloads)
    yield payloads

def generate_uuid():
    temp = str(uuid.uuid4())
    yield temp

async def send_to_coap(payload):
    # payload["key"] = next(generate_uuid())
    payload["timestamp"] = "{!s}".format(datetime.now())
    context = await Context.create_client_context()
    #print(payload["key"])
    request = Message(payload=dumps(payload), code=POST)
    request.opt.uri_host = 'localhost'
    request.opt.uri_path = ("other", "sensor-values")
    await context.request(request).response


def jobs(payloads):
    # payloads = next(generate_samples(message_job, message_type))
    # For sequential sending
    #loop = asyncio.get_event_loop()
    #for i in payloads:
    #   loop.run_until_complete(send_to_coap(i))

    # For parallel sending
    tasks = [asyncio.Task(send_to_coap(payload)) for payload in payloads]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*tasks))
    loop.close()


def main(job=1, message_job=1, message_type=False):
    for i in range(job):
        payloads = next(generate_samples(message_job, message_type))
        p = Process(target=jobs, args=(payloads,))
        p.start()
        p.join()

#main(job=10, message_type=True)
