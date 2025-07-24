import azure.functions as func
import datetime
import json
import logging
import os
import time
from azure.iot.hub import IoTHubRegistryManager
from azure.iot.hub.models import CloudToDeviceMethod

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

COOLDOWN_SECONDS = 10  # seconds

# Simple in-memory storage for local testing
status_storage = {
    "device_id": "",
    "soil_moisture": 0,
    "relay_status": "UNKNOWN",
    "timestamp": datetime.datetime.utcnow().isoformat(),
    "last_trigger_time": 0
}

def is_cooldown_active():
    return time.time() - status_storage.get('last_trigger_time', 0) < COOLDOWN_SECONDS

def update_last_trigger_time():
    status_storage['last_trigger_time'] = time.time()

def update_status(new_status):
    status_storage.update(new_status)
    status_storage['timestamp'] = datetime.datetime.utcnow().isoformat()

@app.event_hub_message_trigger(
    arg_name="azeventhub",
    event_hub_name="iothub-ehub-soil-moist-56760334-6b590c3b84",
    connection="IOT_HUB_CONNECTION_STRING",
    cardinality=func.Cardinality.ONE
)
def eventhub_trigger(azeventhub: func.EventHubEvent):
    body = json.loads(azeventhub.get_body().decode('utf-8'))
    device_id = azeventhub.iothub_metadata['connection-device-id']

    logging.info(f'Received message: {body} from {device_id}')
    soil_moisture = body['soil_moisture']

    if is_cooldown_active():
        logging.info('Cooldown active. Skipping direct method call.')
        return

    relay_status = "OFF"
    if soil_moisture > 450:
        direct_method = CloudToDeviceMethod(method_name='relay_on', payload='{}')
        relay_status = "ON"
    else:
        direct_method = CloudToDeviceMethod(method_name='relay_off', payload='{}')
        relay_status = "OFF"

    logging.info(f'Sending direct method: {direct_method.method_name} to {device_id}')
    
    try:
        registry_manager_connection_string = os.environ['REGISTRY_MANAGER_CONNECTION_STRING']
        registry_manager = IoTHubRegistryManager(registry_manager_connection_string)
        registry_manager.invoke_device_method(device_id, direct_method)
        
        update_last_trigger_time()
        update_status({
            "device_id": device_id,
            "soil_moisture": soil_moisture,
            "relay_status": relay_status
        })
        
        logging.info('Direct method sent and cooldown time updated.')
    except Exception as e:
        logging.error(f"Failed to invoke method or save status: {e}")

@app.function_name(name="get_status")
@app.route(route="status", auth_level=func.AuthLevel.ANONYMOUS)
def get_status(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Status HTTP trigger function called.')
    try:
        return func.HttpResponse(
            json.dumps(status_storage),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Error retrieving status: {e}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

@app.function_name(name="relay_on")
@app.route(route="relay_on", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def relay_on(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Manual relay_on HTTP trigger function processed.')
    logging.info(f'Request URL: {req.url}')
    logging.info(f'Request method: {req.method}')
    logging.info(f'Request params: {dict(req.params)}')
    try:
        body = req.get_body().decode('utf-8')
        logging.info(f'Request body: {body}')
    except:
        logging.info('Could not decode request body')
    return handle_relay_request(req, "ON")

@app.function_name(name="relay_off")
@app.route(route="relay_off", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def relay_off(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Manual relay_off HTTP trigger function processed.')
    logging.info(f'Request URL: {req.url}')
    logging.info(f'Request method: {req.method}')
    logging.info(f'Request params: {dict(req.params)}')
    try:
        body = req.get_body().decode('utf-8')
        logging.info(f'Request body: {body}')
    except:
        logging.info('Could not decode request body')
    return handle_relay_request(req, "OFF")

def handle_relay_request(req: func.HttpRequest, action: str):
    try:
        logging.info(f'Processing relay request for action: {action}')
        
        device_id = req.params.get('device_id')
        logging.info(f'Device ID from params: {device_id}')
        
        if not device_id:
            try:
                req_body = req.get_json()
                logging.info(f'Request body JSON: {req_body}')
                if req_body:
                    device_id = req_body.get('device_id')
                    logging.info(f'Device ID from body: {device_id}')
            except ValueError as e:
                logging.error(f'Error parsing JSON body: {e}')
                pass

        if not device_id:
            logging.error('No device_id found in request')
            return func.HttpResponse(
                "Please provide device_id in query string or request body.",
                status_code=400
            )

        method_name = f'relay_{action.lower()}'
        direct_method = CloudToDeviceMethod(method_name=method_name, payload='{}')
        
        logging.info(f'Manual control: Sending direct method: {method_name} to {device_id}')
        
        # Check if environment variable exists
        registry_manager_connection_string = os.environ.get('REGISTRY_MANAGER_CONNECTION_STRING')
        if not registry_manager_connection_string:
            logging.error('REGISTRY_MANAGER_CONNECTION_STRING environment variable not found')
            return func.HttpResponse(
                "Configuration error: Missing connection string",
                status_code=500
            )
        
        registry_manager = IoTHubRegistryManager(registry_manager_connection_string)

        logging.info('Attempting to invoke device method...')
        registry_manager.invoke_device_method(device_id, direct_method)
        logging.info('Device method invoked successfully')
        
        update_status({
            "device_id": device_id,
            "relay_status": action
        })

        return func.HttpResponse(
            f"Relay turned {action} successfully for device: {device_id}",
            status_code=200
        )
    except Exception as e:
        logging.error(f'Error in manual relay control: {str(e)}')
        return func.HttpResponse(
            f"Error turning relay {action}: {str(e)}",
            status_code=500
        )