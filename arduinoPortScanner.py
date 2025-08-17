import serial.tools.list_ports
import serial
import time

def scan_arduino_ports():
    """Scan for available Arduino ports"""
    print("🔍 Scanning for available Arduino ports...")
    print("=" * 50)
    
    # List all available ports
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        print("❌ No serial ports found!")
        return []
    
    available_ports = []
    
    for port in ports:
        print(f"Port: {port.device}")
        print(f"  Description: {port.description}")
        print(f"  Manufacturer: {port.manufacturer}")
        print(f"  Hardware ID: {port.hwid}")
        
        # Check if it's likely an Arduino
        is_arduino = False
        if port.description and any(keyword in port.description.lower() for keyword in ['arduino', 'ch340', 'cp210x', 'ftdi']):
            is_arduino = True
        if port.manufacturer and 'arduino' in port.manufacturer.lower():
            is_arduino = True
            
        if is_arduino:
            print("  ✅ Likely Arduino device!")
            available_ports.append(port.device)
        
        print("-" * 30)
    
    return available_ports

def test_arduino_connection(port, baudrate=9600):
    """Test connection to Arduino"""
    try:
        print(f"🔌 Testing connection to {port} at {baudrate} baud...")
        
        # Try to open the port
        ser = serial.Serial(port, baudrate, timeout=2)
        time.sleep(3)  # Wait for Arduino to reset
        
        print("✅ Port opened successfully!")
        
        # Try to read data for a few seconds
        start_time = time.time()
        data_received = False
        
        while time.time() - start_time < 5:  # Wait up to 5 seconds
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        print(f"📡 Received: {line}")
                        data_received = True
                        break
                except:
                    pass
            time.sleep(0.1)
        
        ser.close()
        
        if data_received:
            print(f"✅ {port} is working and sending data!")
            return True
        else:
            print(f"⚠️ {port} opened but no data received (Arduino might not be running your code)")
            return False
            
    except serial.SerialException as e:
        print(f"❌ Failed to connect to {port}: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error with {port}: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Arduino Connection Diagnostic Tool")
    print("=" * 50)
    
    # Scan for ports
    arduino_ports = scan_arduino_ports()
    
    if not arduino_ports:
        print("\n❌ No Arduino devices detected.")
        print("\n🔧 Troubleshooting suggestions:")
        print("1. Make sure your Arduino is connected via USB")
        print("2. Install Arduino drivers if needed")
        print("3. Try a different USB cable")
        print("4. Check if Arduino IDE can detect the device")
    else:
        print(f"\n🎯 Found {len(arduino_ports)} potential Arduino port(s)")
        
        # Test each Arduino port
        for port in arduino_ports:
            print(f"\n{'='*20} Testing {port} {'='*20}")
            test_arduino_connection(port)
    
    input("\nPress Enter to exit...")