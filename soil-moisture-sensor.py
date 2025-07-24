from counterfit_connection import CounterFitConnection
CounterFitConnection.init('127.0.0.1', 3000)

import time
from counterfit_shims_grove.adc import ADC
from counterfit_shims_grove.grove_relay import GroveRelay
import json
from azure.iot.device import IoTHubDeviceClient, Message, MethodResponse, X509
import logging

# Enable logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

host_name = "soil-moisture-sensor-aicha19.azure-devices.net"
device_id = "soil-moisture-sensor-x509"
x509 = X509("./soil-moisture-sensor-x509-cert.pem", "./soil-moisture-sensor-x509-key.pem")

# Initialize hardware
adc = ADC()
relay = GroveRelay(5)

# Create device client
device_client = IoTHubDeviceClient.create_from_x509_certificate(x509, host_name, device_id)

def handle_method_request(request):
    print(f"Direct method received - {request.name}")
    logger.info(f"Direct method received - {request.name} with payload: {request.payload}")
    
    method_response = None
    
    try:
        if request.name == "relay_on":
            print("Turning relay ON")
            relay.on()
            print("Relay is now ON")
            method_response = MethodResponse.create_from_method_request(request, 200, "Relay turned ON")
            
        elif request.name == "relay_off":
            print("Turning relay OFF")
            relay.off()
            print("Relay is now OFF")
            method_response = MethodResponse.create_from_method_request(request, 200, "Relay turned OFF")
            
        else:
            print(f"Unknown method: {request.name}")
            method_response = MethodResponse.create_from_method_request(request, 404, f"Unknown method: {request.name}")
    
    except Exception as e:
        print(f"Error handling method {request.name}: {e}")
        logger.error(f"Error handling method {request.name}: {e}")
        method_response = MethodResponse.create_from_method_request(request, 500, f"Error: {str(e)}")
    
    # Send the response
    device_client.send_method_response(method_response)
    print(f"Method response sent: {method_response.status}")

print('Connecting to IoT Hub...')
try:
    device_client.connect()
    print('Connected successfully!')
    logger.info('Device connected to IoT Hub')
    
    # Set the method request handler
    device_client.on_method_request_received = handle_method_request
    print('Method request handler set')
    
except Exception as e:
    print(f'Connection failed: {e}')
    logger.error(f'Connection failed: {e}')
    exit(1)

# Main loop
try:
    while True:
        try:
            soil_moisture = adc.read(0)
            print(f"Soil moisture: {soil_moisture}")
            
            telemetry = {'soil_moisture': soil_moisture}
            message = Message(json.dumps(telemetry))
            
            print(f"Sending telemetry: {telemetry}")
            device_client.send_message(message)
            print("Telemetry sent successfully")
            
            time.sleep(11)
            
        except Exception as e:
            print(f"Error in main loop: {e}")
            logger.error(f"Error in main loop: {e}")
            time.sleep(5)  # Wait before retrying

except KeyboardInterrupt:
    print("Shutting down...")
    
finally:
    print("Disconnecting...")
    device_client.shutdown()