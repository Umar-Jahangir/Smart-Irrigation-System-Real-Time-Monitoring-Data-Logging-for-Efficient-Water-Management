#include <Wire.h>
#include "RTClib.h"

// Pin definitions
const int moistureSensorPin = A0;  // Analog input
const int relayPin = 8;

// Water flow parameters
float flowRate = 1.0; // liters per minute
unsigned long pumpStartTime = 0;
float totalWaterUsed = 0.0;
float todayWaterUsed = 0.0;
unsigned int wateringEventsToday = 0;

// Moisture thresholds (calibrate these!)
int dryThreshold = 600;  // Higher value = drier soil (adjust after calibration)
int wetThreshold = 300;  // Lower value = wetter soil (adjust after calibration)

RTC_DS3231 rtc;

void setup() {
  Serial.begin(9600);
  while (!Serial); // Wait for serial connection
  
  pinMode(relayPin, OUTPUT);
  digitalWrite(relayPin, HIGH); // Start with pump OFF (active LOW relay)
  
  if (!rtc.begin()) {
    Serial.println("ERROR: RTC not found");
    while (1);
  }

  if (rtc.lostPower()) {
    Serial.println("WARNING: RTC lost power, resetting time");
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }

  Serial.println("System ready");
  Serial.println("-------------------");
  Serial.println("Calibration Mode:");
  Serial.print("Dry Threshold: "); Serial.println(dryThreshold);
  Serial.print("Wet Threshold: "); Serial.println(wetThreshold);
  Serial.println("-------------------");
}

void loop() {
  // Read analog moisture value (0-1023)
  int moistureValue = analogRead(moistureSensorPin);
  
  Serial.print("Moisture: ");
  Serial.print(moistureValue);
  
  // Control logic
  if (moistureValue > dryThreshold) {
    Serial.println(" - DRY (Needs water)");
    if (digitalRead(relayPin) == HIGH) { // If pump is off
      startWatering();
    }
  } 
  else if (moistureValue < wetThreshold) {
    Serial.println(" - WET (Enough water)");
    if (digitalRead(relayPin) == LOW) { // If pump is on
      stopWatering();
    }
  } 
  else {
    Serial.println(" - OK (Moisture adequate)");
  }
  sendIrrigationData();
  delay(2000); // 2 second delay between readings
}

void startWatering() {
  digitalWrite(relayPin, LOW); // Activate relay (LOW=ON for active LOW relays)
  pumpStartTime = millis();
  Serial.println("ACTION: Pump STARTED");
}

void stopWatering() {
  digitalWrite(relayPin, HIGH); // Deactivate relay
  unsigned long durationMinutes = (millis() - pumpStartTime) / 60000;
  float litersUsed = flowRate * durationMinutes;
  
  // Update totals
  totalWaterUsed += litersUsed;
  todayWaterUsed += litersUsed;
  wateringEventsToday++;

  // Print report
  Serial.print("ACTION: Pump STOPPED after ");
  Serial.print(durationMinutes, 1);
  Serial.print(" minutes, used ");
  Serial.print(litersUsed, 2);
  Serial.println(" liters");
  Serial.println("-------------------");
}

void sendIrrigationData() {
  Serial.print("IRRIGATION_DATA:");  // Make sure this matches Python's expectation
  Serial.print("MOISTURE="); Serial.print(analogRead(moistureSensorPin)); 
  Serial.print(",PUMP="); Serial.print(digitalRead(relayPin) == LOW ? 1 : 0); // 1=ON, 0=OFF
  Serial.print(",WATER_USED="); Serial.print(todayWaterUsed, 2);
  Serial.print(",EVENTS="); Serial.print(wateringEventsToday);
  Serial.print(",TOTAL="); Serial.print(totalWaterUsed, 2);
  Serial.println(); // Ensure newline at end
}
