void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  Serial.println("arduino ready"); // all prints followed by '\r'
}

void loop() {
  // put your main code here, to run repeatedly:
  while (!Serial.available()) {   }

  String line = Serial.readStringUntil('\r');
  Serial.println("hi");
}
