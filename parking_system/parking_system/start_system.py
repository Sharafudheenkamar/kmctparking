import os
import subprocess
import time
import threading

def start_django_server():
    """Start Django development server"""
    print("🚀 Starting Django server...")
    os.system("python manage.py runserver")

def start_arduino_reader():
    """Start Arduino reader script"""
    time.sleep(3)  # Wait for Django to start
    print("🔌 Starting Arduino reader...")
    os.system("python arduino_reader.py")

def main():
    print("🏁 Starting Smart Parking System...")
    
    # Start Django server in a separate thread
    django_thread = threading.Thread(target=start_django_server)
    django_thread.daemon = True
    django_thread.start()
    
    # Start Arduino reader
    start_arduino_reader()

if __name__ == "__main__":
    main()
