# IOT-based-Soilmoisture-Sensor-with-Water-supply-Monitoring-System

A **Smart Irrigation System** that automatically monitors soil moisture, controls water supply using a pump and relay, and records real-time irrigation data with a Python-based dashboard. The system ensures efficient water management by logging daily, monthly, and yearly usage, while providing visualization and export options.

---

## ✨ Features
- 🌿 **Automatic Irrigation** – Waters plants only when soil is dry.  
- 📊 **Real-Time Monitoring** – Live soil moisture, pump status, and water usage.  
- ⏱ **Accurate Logging** – DS3231 RTC timestamps irrigation events.  
- 📈 **Analytics Dashboard** – Graphs for per-minute, hourly, daily, monthly, and yearly usage.  
- 💾 **Data Export** – Save logs in JSON and CSV formats.  
- 🔌 **Extendable** – Supports Bluetooth/Wi-Fi modules for IoT integration.  

---

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/da44ec2c-f268-4cb1-a237-6793e2ce69e7" />

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/32cf93f1-b0b8-44a9-883e-b46869c4ce43" />

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/ecd62a37-64e6-4120-ba51-be8327a7809f" />

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/9ca7528b-4409-41b4-90e3-ca085b04d691" />

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/9b4cb18a-0413-4c41-99d9-7052289e225c" />

---
## 🔧 Hardware Components
| Component                | Quantity | Description                                                                 |
|--------------------------|----------|-----------------------------------------------------------------------------|
| Arduino UNO              | 1        | Microcontroller board for controlling the system                            |
| Soil Moisture Sensor     | 1        | Detects soil dryness/wetness                                                |
| Relay Module             | 1        | Acts as a switch to control the water pump                                  |
| Water Pump               | 1        | Supplies water to the plants                                                |
| DS3231 RTC Module        | 1        | Provides accurate real-time timestamps                                      |
| Power Supply             | 1        | Powers Arduino and pump                                                     |
| HC-05 Bluetooth Module *(optional)* | 1 | Wireless data transfer for IoT dashboard integration                        |

---

## ⚡ Circuit Connections
| Arduino Pin  | Connected To                |
|--------------|-----------------------------|
| A0           | Soil Moisture Sensor Output |
| D7           | Relay IN Pin (Pump Control) |
| SDA          | DS3231 RTC SDA              |
| SCL          | DS3231 RTC SCL              |
| VCC (5V)     | Sensor, RTC, Relay VCC      |
| GND          | Common Ground               |

---

## 💻 Software & Technologies
- **Embedded C (Arduino IDE)** – for Arduino UNO firmware  
- **Python (Tkinter, Matplotlib, JSON, CSV)** – for real-time dashboard  
- **Serial Communication** – Arduino ↔ Python  
- **Optional IoT modules** – Bluetooth/Wi-Fi for remote monitoring  

---

## 🚀 Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/Umar-Jahangir/Smart-Irrigation-System-Real-Time-Monitoring-Data-Logging-for-Efficient-Water-Management.git
cd Smart-Irrigation-System-Real-Time-Monitoring-Data-Logging-for-Efficient-Water-Management

---

### 2️⃣ Setup Python Environment
python -m venv venv
venv\Scripts\activate       # On Windows
source venv/bin/activate    # On Linux/Mac

---

### 3️⃣ Install Dependencies
pip install pyserial matplotlib pandas numpy

### ▶️ Usage
Upload Arduino Code
Open Irrigating/Irrigating.ino in Arduino IDE
Select Arduino UNO board
Upload to the board
Run Dashboard
python smart_irrigation_dashboard.py

This will open the Smart Irrigation Dashboard GUI with tabs for:
Current Status
Recent Activity
Graphs (every minute, Daily, Monthly, Yearly Trends)
Data Export

⚙️ Configuration
Update COM Port in smart_irrigation_dashboard.py (port='COM6') as per your Arduino connection.
Modify Flow Rate (L/min) in the Python file to match your pump’s specifications.

🤝 Contributing
Fork the repo
Create a new branch (git checkout -b feature-xyz)
Commit changes (git commit -m "Added feature xyz")
Push to branch (git push origin feature-xyz)
Open a Pull Request 🎉

🏭 Industrial Applications
Smart Farming / Agriculture
Greenhouses
Home Gardening
Water Conservation Projects






