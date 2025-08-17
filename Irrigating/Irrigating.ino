#include <Wire.h>
#include "RTClib.h"

RTC_DS3231 rtc;

// Pin definitions
#define RELAY_PIN 3
#define SOIL_PIN 6   // Digital output from soil moisture sensor

// Flow Rate in liters/minute (adjust based on your pump)
float flowRate = 1.0;  

// Variables
bool pumpStatus = false;
bool prevPumpStatus = false;
unsigned long pumpStartTime = 0;
float totalWaterUsed = 0.0;
float waterUsedToday = 0.0;
int wateringEventsToday = 0;

DateTime lastDate;

void setup() {
  Serial.begin(9600);
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(SOIL_PIN, INPUT);
  
  // Make sure pump is OFF initially
  digitalWrite(RELAY_PIN, HIGH);  // HIGH = OFF for most relay modules

  if (!rtc.begin()) {
    Serial.println("RTC not found!");
    while (1);
  }

  if (rtc.lostPower()) {
    // Set RTC to compile time if power lost
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }

  lastDate = rtc.now();
  
  Serial.println("Smart Irrigation System Started");
  Serial.println("Digital Soil Sensor Logic (CORRECTED):");
  Serial.println("- HIGH = DRY soil (pump ON)");
  Serial.println("- LOW = WET soil (pump OFF)");
}

void loop() {
  DateTime now = rtc.now();

  // Reset daily water usage at midnight
  if (now.day() != lastDate.day()) {
    waterUsedToday = 0;
    wateringEventsToday = 0;
    Serial.println("Daily counters reset - New day!");
  }
  lastDate = now;

  int soilStatus = digitalRead(SOIL_PIN);
  
  // Debug: Print raw sensor reading
  Serial.print("Raw sensor: "); Serial.println(soilStatus == HIGH ? "HIGH (DRY)" : "LOW (WET)");

  // CORRECTED Soil sensor logic:
  // HIGH (1) = DRY soil → turn pump ON
  // LOW (0) = WET soil → turn pump OFF
  if (soilStatus == HIGH) {
    // Soil is DRY - turn pump ON
    if (!pumpStatus) {
      Serial.println(">>> SOIL DRY - TURNING PUMP ON <<<");
      pumpStartTime = millis();
      wateringEventsToday++;
    }
    digitalWrite(RELAY_PIN, LOW);  // RELAY ON (most relays are active LOW)
    pumpStatus = true;
  } 
  else {
    // Soil is WET - turn pump OFF
    if (pumpStatus) {
      Serial.println(">>> SOIL WET - TURNING PUMP OFF <<<");
      unsigned long durationMs = millis() - pumpStartTime;
      float durationMin = durationMs / 60000.0; // convert ms → minutes
      float waterSupplied = flowRate * durationMin;
      waterUsedToday += waterSupplied;
      totalWaterUsed += waterSupplied;
      
      Serial.print("Watering completed: ");
      Serial.print(durationMin, 2);
      Serial.print(" minutes, ");
      Serial.print(waterSupplied, 2);
      Serial.println(" liters");
    }
    digitalWrite(RELAY_PIN, HIGH); // RELAY OFF (most relays are active LOW)
    pumpStatus = false;
  }

  prevPumpStatus = pumpStatus;

  // Send data to Python Dashboard
  // For dashboard compatibility: send higher number when DRY, lower when WET
  int moistureDisplay = (soilStatus == HIGH) ? 700 : 300;  // DRY=700, WET=300
  
  Serial.print("IRRIGATION_DATA:");
  Serial.print("MOISTURE="); Serial.print(moistureDisplay);
  Serial.print(",PUMP="); Serial.print(pumpStatus ? 1 : 0);
  Serial.print(",WATER_USED="); Serial.print(waterUsedToday, 2);
  Serial.print(",TOTAL="); Serial.print(totalWaterUsed, 2);
  Serial.print(",EVENTS="); Serial.print(wateringEventsToday);
  Serial.print(",TIME="); 
  
  // Format time with leading zeros
  Serial.print(now.year()); Serial.print("-");
  if (now.month() < 10) Serial.print("0");
  Serial.print(now.month()); Serial.print("-");
  if (now.day() < 10) Serial.print("0");
  Serial.print(now.day()); Serial.print(" ");
  if (now.hour() < 10) Serial.print("0");
  Serial.print(now.hour()); Serial.print(":");
  if (now.minute() < 10) Serial.print("0");
  Serial.print(now.minute()); Serial.print(":");
  if (now.second() < 10) Serial.print("0");
  Serial.print(now.second());
  Serial.println();

  delay(2000); // send update every 2s
}