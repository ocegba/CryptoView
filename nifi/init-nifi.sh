#!/bin/bash

NIFI_URL=https://localhost:8443/nifi-api
TEMPLATE_NAME="binance_template"
USERNAME="admin"
PASSWORD="ctsBtRBKHRAx69EqUghvvgEvjnaLjFEB"

# Fonction pour obtenir le jeton JWT
get_token() {
  echo "Obtaining JWT token..."
  TOKEN=$(curl -k -X POST -H "Content-Type: application/x-www-form-urlencoded" -d "username=$USERNAME&password=$PASSWORD" "$NIFI_URL/access/token")
  echo "Token obtained."
}

wait_for_nifi() {
  echo "Waiting for NiFi to start..."
  until $(curl -k --output /dev/null --silent --fail -H "Authorization: Bearer $TOKEN" "$NIFI_URL"); do
    printf '.'
    sleep 5
  done
  echo "NiFi started."
}

get_template_id() {
  echo "Retrieving template ID for: $TEMPLATE_NAME"
  TEMPLATES_JSON=$(curl -k -s -H "Authorization: Bearer $TOKEN" "$NIFI_URL/flow/templates")
  TEMPLATE_ID=$(echo "$TEMPLATES_JSON" | jq -r --arg TEMPLATE_NAME "$TEMPLATE_NAME" '.templates[] | select(.template.name==$TEMPLATE_NAME) | .id')
  echo "Template ID: $TEMPLATE_ID"
}

instantiate_template() {
  echo "Instantiating template: $TEMPLATE_ID"
  INSTANCE_RESPONSE=$(curl -k -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d "{\"originX\": 2.0, \"originY\": 3.0, \"templateId\": \"$TEMPLATE_ID\"}" "$NIFI_URL/process-groups/root/template-instance")
  
    # Exécutez l'appel curl pour obtenir les détails du groupe de processus racine
    RESPONSE=$(curl -k -H "Authorization: Bearer $TOKEN" "https://localhost:8443/nifi-api/flow/process-groups/root")

    # Extrait l'ID du groupe de processus racine de la réponse
    PROCESS_GROUP_ID=$(echo "$RESPONSE" | jq -r '.processGroupFlow.id')

    # Vérifie l'ID extrait
    if [[ $PROCESS_GROUP_ID == "null" || -z $PROCESS_GROUP_ID ]]; then
    echo "Failed to extract Process Group ID. Check the response structure."
    exit 1
    else
    echo "Process Group ID: $PROCESS_GROUP_ID"
    fi
}

start_components() {
  echo "Starting components in Process Group: $PROCESS_GROUP_ID"
  START_RESPONSE=$(curl -k -X PUT -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d "{\"id\":\"$PROCESS_GROUP_ID\",\"state\":\"RUNNING\"}" "$NIFI_URL/flow/process-groups/$PROCESS_GROUP_ID")
  echo "Components started."
}

wait_for_nifi
get_token
get_template_id
instantiate_template
start_components
