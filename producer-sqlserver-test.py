#!/usr/bin/env python

from confluent_kafka import Producer, KafkaError
import json
import ccloud_lib

import pymssql


if __name__ == '__main__':

    # Read arguments and configurations and initialize
    args = ccloud_lib.parse_args()
    config_file = args.config_file
    topic = args.topic
    conf = ccloud_lib.read_ccloud_config(config_file)

    # Create Producer instance
    producer_conf = ccloud_lib.pop_schema_registry_params_from_config(conf)
    producer = Producer(producer_conf)

    # Create topic if needed
    ccloud_lib.create_topic(conf, topic)

    delivered_records = 0

    # Optional per-message on_delivery handler (triggered by poll() or flush())
    # when a message has been successfully delivered or
    # permanently failed delivery (after retries).
    def acked(err, msg):
        global delivered_records
        """Delivery report handler called on
        successful or failed delivery of message
        """
        if err is not None:
            print("Failed to deliver message: {}".format(err))
        else:
            delivered_records += 1
            print("Produced record to topic {} partition [{}] @ offset {}"
                  .format(msg.topic(), msg.partition(), msg.offset()))


    # Process messages
    # Connection SQL Server
    conn = pymssql.connect(
        host=r'HOSTNAME-IP',
        user=r'USER',
        password='PASS',
        database='DB'
    )
    cursor = conn.cursor(as_dict=True)
    # Get 10 rows
    cursor.execute(' SELECT TOP 10 ActionTypeKey, Name FROM Runtime.dbo.ActionType ')
    for row in cursor:
        record_key = row['ActionTypeKey']
        record_value = json.dumps({'id': row['ActionTypeKey'], 'name': row['Name']})
        print("Producing record: {}\t{}".format(record_key, record_value))
        producer.produce(topic, key=record_key, value=record_value, on_delivery=acked)
        # p.poll() serves delivery reports (on_delivery)
        # from previous produce() calls.
        producer.poll(0)

    producer.flush()
    conn.close()
    print("{} messages were produced to topic {}!".format(delivered_records, topic))
