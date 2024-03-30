#!/bin/bash 

# A brief pause to ensure Kafka Connect is fully operational
sleep 30

echo "Submitting connector configuration to Kafka Connect"
curl --connect-timeout 5 \
    --max-time 10 \
    --retry 5 \
    --retry-delay 0 \
    --retry-max-time 40 -X POST -H "Content-Type: application/json" --data @./config/elasticsearch-sink.json http://localhost:8083/connectors
echo "Connector configuration submission attempted"