import serial
import time
import requests
import json
from django.conf import settings
import os
import django
from parking_system.models import ParkingSlot


# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parking_system.settings')
django.setup()


class ArduinoReader:
    def __init__(self, port='COM3', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.arduino = None
        self.base_url = 'http://127.0.0.1:8000'
        
    def connect_arduino(self):
        """Connect to Arduino via serial port"""
        try:
            self.arduino = serial.Serial(self.port, self.baudrate)
            time.sleep(2)  # Wait for Arduino to initialize
            print(f"✅ Connected to Arduino on {self.port}")
            return True
        except Exception as e:
            print(f"❌ Error connecting to Arduino: {e}")
            return False
    
    def read_serial_data(self):
        """Continuously read data from Arduino"""
        if not self.arduino:
            print("❌ Arduino not connected")
            return
            
        print("🔄 Starting to read Arduino data...")
        
        while True:
            try:
                if self.arduino.in_waiting > 0:
                    # Read line from Arduino
                    data = self.arduino.readline().decode('utf-8').strip()
                    print(f"📨 Received: {data}")
                    
                    # Parse slot data
                    if data.startswith("SLOT_DATA:"):
                        self.parse_and_update_slots(data)
                        
                time.sleep(0.5)  # Small delay
                
            except KeyboardInterrupt:
                print("\n⏹️ Stopping Arduino reader...")
                break
            except Exception as e:
                print(f"❌ Error reading serial data: {e}")
                time.sleep(1)
                
        self.disconnect_arduino()
    
    def parse_and_update_slots(self, data):
        """Parse Arduino data and update Django database"""
        try:
            # Extract slot data: "SLOT_DATA:0,1,0,1,2"
            slot_values = data.split(":")[1].split(",")
            
            slot_data = {
                'S1': int(slot_values[0]),
                'S2': int(slot_values[1]),
                'S3': int(slot_values[2]),
                'S4': int(slot_values[3]),
                'vacant_slots': int(slot_values[4])
            }
            
            print(f"📊 Parsed data: {slot_data}")
            
            # Update database directly or via API
            self.update_database(slot_data)
            
        except Exception as e:
            print(f"❌ Error parsing slot data: {e}")
    
    def update_database(self, slot_data):
        """Update Django database with slot status"""
        try:
            # Map slot names to database entries
            slot_mapping = {
                'S1': 'A1',  # Adjust these to match your actual slot numbers
                'S2': 'A2',
                'S3': 'B1',
                'S4': 'B2'
            }
            
            # Update each slot
            for arduino_slot, is_occupied in slot_data.items():
                if arduino_slot.startswith('S') and arduino_slot in slot_mapping:
                    db_slot_number = slot_mapping[arduino_slot]
                    
                    try:
                        slot = ParkingSlot.objects.get(slot_number=db_slot_number)
                        slot.is_occupied = bool(is_occupied)
                        slot.save()
                        print(f"✅ Updated {db_slot_number}: {'Occupied' if is_occupied else 'Available'}")
                    except ParkingSlot.DoesNotExist:
                        print(f"⚠️ Slot {db_slot_number} not found in database")
            
            # Also update via API for real-time notifications
            self.send_api_update(slot_data)
            
        except Exception as e:
            print(f"❌ Error updating database: {e}")
    
    def send_api_update(self, slot_data):
        """Send update to Django API for real-time notifications"""
        try:
            response = requests.post(
                f'{self.base_url}/api/slots/update/',
                json=slot_data,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            
            if response.status_code == 200:
                print("✅ API update successful")
            else:
                print(f"⚠️ API update failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error sending API update: {e}")
    
    def disconnect_arduino(self):
        """Disconnect from Arduino"""
        if self.arduino and self.arduino.is_open:
            self.arduino.close()
            print("🔌 Disconnected from Arduino")

def main():
    # Initialize Arduino reader
    reader = ArduinoReader(port='COM3', baudrate=9600)  # Adjust port as needed
    
    # Connect and start reading
    if reader.connect_arduino():
        reader.read_serial_data()
    else:
        print("❌ Failed to connect to Arduino. Please check:")
        print("   1. Arduino is connected via USB")
        print("   2. Correct COM port (check Device Manager on Windows)")
        print("   3. Arduino sketch is uploaded and running")
        print("   4. No other program is using the COM port")

if __name__ == "__main__":
    main()
