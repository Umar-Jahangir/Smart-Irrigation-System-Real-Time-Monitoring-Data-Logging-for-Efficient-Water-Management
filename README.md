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

### 2️⃣ Setup Python Environment
python -m venv venv
venv\Scripts\activate       # On Windows
source venv/bin/activate    # On Linux/Mac
