import paho.mqtt.client as mqtt
import json
import os

class IoTBridge:
    def __init__(self, broker="localhost", port=1883, client_id="spark_agent"):
        """
        Initializes the MQTT client for IoT communication.
        """
        self.broker = os.getenv("MQTT_BROKER", broker)
        self.port = int(os.getenv("MQTT_PORT", port))
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        
        # In a real scenario, we would fetch username/password from the Vault
        # For now, we assume a local unsecured broker or environment variables
        self.username = os.getenv("MQTT_USER")
        self.password = os.getenv("MQTT_PASSWORD")
        
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)

        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            print(f"[IOT] Connected to MQTT broker at {self.broker}:{self.port}")
        except Exception as e:
            print(f"[IOT] Failed to connect to MQTT broker: {e}")

    def set_device_state(self, topic, state):
        """
        Publishes a state set command to the specified topic.
        Standardizes on JSON payloads: {"state": "ON"/"OFF"}
        """
        payload = json.dumps({"state": state})
        result = self.client.publish(topic, payload)
        status = result[0]
        if status == 0:
            print(f"[IOT] Published to {topic}: {payload}")
            return f"Command sent: {state} to {topic}"
        else:
            print(f"[IOT] Failed to publish to {topic}")
            return f"Failed to send command to {topic}"

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

# Global instance
iot_bridge = IoTBridge()

if __name__ == "__main__":
    # Poltergeist Test (Dry Run / Local verification if possible)
    # This requires an MQTT broker running to fully PASS, but we can verify the payload structure.
    print("--- Running Poltergeist Test (Simulation) ---")
    bridge = IoTBridge(broker="localhost") # Will log failure if no broker
    res = bridge.set_device_state("home/test/light/set", "ON")
    print(f"Result: {res}")
