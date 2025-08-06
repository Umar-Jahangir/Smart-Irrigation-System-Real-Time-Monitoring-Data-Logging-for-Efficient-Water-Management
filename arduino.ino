#include <Wire.h>
#include "RTClib.h"

RTC_DS3231 rtc;

int relayPin = 3;        // pin to control relay
int soilPin = 6;         // pin from soil moisture sensor

bool motorIsOn = false;
DateTime startTime;
DateTime stopTime;

float totalWaterLiters = 0.0;
float flowRate = 1.0;    // liters per minute

void setup() {
  Serial.begin(115200);

  pinMode(relayPin, OUTPUT);
  pinMode(soilPin, INPUT);

  if (!rtc.begin()) {
    Serial.println("❌ Couldn't find RTC");
    while (1);
  }

  if (rtc.lostPower()) {
    Serial.println("⚠️ RTC lost power, setting time to compile time");
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__))); // set to current time
  }

  Serial.println("🌱 Watering System Started");
}

void loop() {
  int soil = digitalRead(soilPin);
  Serial.print("Soil reading: ");
  Serial.println(soil);

  if (soil == LOW && motorIsOn) {
    // Soil is wet → stop watering
    digitalWrite(relayPin, HIGH);
    motorIsOn = false;
    stopTime = rtc.now();

    TimeSpan duration = stopTime - startTime;
    float seconds = duration.totalseconds();
    float litersUsed = (seconds / 60.0) * flowRate;
    totalWaterLiters += litersUsed;

    Serial.println("💧 Watering stopped.");
    Serial.print("⏱️ Duration: ");
    Serial.print(seconds);
    Serial.print(" sec (");
    Serial.print(seconds / 60.0);
    Serial.println(" min)");

    Serial.print("📦 Water used: ");
    Serial.print(litersUsed, 2);
    Serial.println(" L");

    Serial.print("📊 Total so far: ");
    Serial.print(totalWaterLiters, 2);
    Serial.println(" L");
    Serial.println("---------------------------");
  }

  else if (soil == HIGH && !motorIsOn) {
    // Soil is dry → start watering
    digitalWrite(relayPin, LOW);
    motorIsOn = true;
    startTime = rtc.now();

    Serial.println("🟢 Watering started at: ");
    printDateTime(startTime);
  }

  delay(1000);
}

void printDateTime(DateTime dt) {
  Serial.print(dt.day());
  Serial.print("/");
  Serial.print(dt.month());
  Serial.print("/");
  Serial.print(dt.year());
  Serial.print(" ");
  Serial.print(dt.hour());
  Serial.print(":");
  Serial.print(dt.minute());
  Serial.print(":");
  Serial.println(dt.second());
}
