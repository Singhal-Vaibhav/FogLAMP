from datetime import datetime

import sqlalchemy as sa

_connection_string = "postgres:///foglamp"


def _read_statistics(_read_sensor_value_map):
    f = open("latency.csv", "w")
    f.write("Key, send_ts(t1), t1_diff, received_ts(t2), t2_diff, write_ts(t4), t4_diff, coap_latency, time_diff(t4-t1)\n")
    qr = "SELECT read_key, user_ts, ts from readings order by user_ts asc"
    engine = sa.create_engine(_connection_string, pool_size=20, max_overflow=0)
    conn = engine.connect()
    query_result = conn.execute(qr)
    previous_t1 = None
    previous_t2 = None
    previous_t4 = None
    for row in query_result:
        # print("Row", row[0], row[1], row[2])
        t_diff_e2e = (row[2] - row[1]).microseconds
        coap_latency = (row[2].replace(tzinfo=None) - _read_sensor_value_map[str(row[0])]).microseconds
        _t2 = _read_sensor_value_map[str(row[0])]
        t1_diff = (row[1] - previous_t1).microseconds if previous_t1 is not None else ''
        t2_diff = (_t2 - previous_t2).microseconds if previous_t2 is not None else ''
        t4_diff = (row[2] - previous_t4).microseconds if previous_t4 is not None else ''
        previous_t1 = row[1]
        previous_t4 = row[2]
        # print(row[1], row[2], t_diff_e2e.microseconds)
        f.write("{},{},{},{},{},{},{},{},{}\n".format(row[0], row[1], t1_diff, _t2, t2_diff, row[2], t4_diff, coap_latency, t_diff_e2e))
        previous_t2 = _t2
    f.close()


def _append_value_from_sensor_log():
    _key_send_map = {}
    f = open('../../src/python/perf.log', 'r')
    for line in f:
        _key_send_map[(line.split('|')[4]).split(' ')[2]] = datetime.strptime(line.split('|')[-1].strip(),
                                                                              "%Y-%m-%d %H:%M:%S.%f")

    f.close()
    return _key_send_map


def _load_and_cpu():
    _load_cpu_map = {}
    max_cpu_pct = 0.0
    key = None
    f = open('perf.log', 'r')
    for line in f:
        if 'test_load' in line:
            key = int(((line.split('|')[-1]).split(' ')[-1]).strip())
            max_cpu_pct = 0.0
        else:
            cpu_pct = float((((line.split('|')[4]).split(':')[2]).split(',')[0]).strip())
            if cpu_pct > max_cpu_pct:
                max_cpu_pct = cpu_pct
                if key is not None:
                    _load_cpu_map[key] = max_cpu_pct, datetime.strptime((line.split('|')[1]).strip(),
                                                                        "%m-%d-%Y %H:%M:%S.%f")
    f.close()
    return _load_cpu_map

def gen_csv_from_dict(dict_load_cpu):
    import collections
    dict_load_cpu = collections.OrderedDict(sorted(dict_load_cpu.items()))
    f = open('results.csv', 'w')
    f.write("Load,Max_CPU,Time\n")
    for key in dict_load_cpu.keys():
        f.write("{},{},{}\n".format(key, dict_load_cpu[key][0], dict_load_cpu[key][1]))
    f.close()

_key_send_map = _append_value_from_sensor_log()
_read_statistics(_key_send_map)
load_cpu_map = _load_and_cpu()
gen_csv_from_dict(load_cpu_map)
