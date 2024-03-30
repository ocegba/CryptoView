#!/bin/bash

# Elasticsearch and Kibana details
ELASTICSEARCH_URL="http://localhost:9200"
KIBANA_URL="http://localhost:5601"
INDEX=".kibana"
DASHBOARD_FILE="./export.ndjson"

# Import the dashboard
curl curl --connect-timeout 5 \
    --max-time 10 \
    --retry 5 \
    --retry-delay 0 \
    --retry-max-time 40 -X POST "$KIBANA_URL/api/saved_objects/_import" \
  -H "kbn-xsrf: true" \
  --form file=@$DASHBOARD_FILE