🌱 Soil Moisture IoT System with Azure Functions

This project demonstrates an IoT-based soil moisture monitoring system that automatically controls a relay (e.g., water pump) based on soil moisture levels using Azure IoT Hub and Azure Functions.

🔌 Reads data from a soil moisture sensor (via CounterFit simulator or real device)

☁️ Sends telemetry to Azure IoT Hub

⚙️ Uses Azure Function triggered by Event Hub to check the moisture level

🔁 Sends a command back to the device to toggle the relay

📷 Project Architecture

[Soil Sensor] --> [IoT Device Code (Python)] --> [Azure IoT Hub/Event Hub] --> [Azure Function] --> [Direct Method to Device] --> [Relay ON/OFF]

🔧 Technologies Used

- Azure IoT Hub

- Azure Functions (Python trigger)

- CounterFit (IoT Simulator) (or real sensor)

- Python 3.9

- MQTT / Event Hub Integration

- Public/Private X.509 authentication

🙌 Acknowledgments
Created as part of an IoT smart agriculture project using Azure and Python.
