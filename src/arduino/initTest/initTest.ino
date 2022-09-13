#define dirPin 4
#define stepPin 5

void setup() {
  // put your setup code here, to run once:
  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);
  Serial.begin(115200);
}

void loop() {
  // put your main code here, to run repeatedly:
  while (!Serial.available()) {   }

  String line = Serial.readStringUntil('\r');
  int var = line.toInt();
  takeSteps(var);
}

void takeSteps(int steps){
  if (steps < 0){
    // negative steps is dir == LOW
    // writing low to dirPin means steps will be taken downward
    digitalWrite(dirPin, LOW);
    steps = steps * -1; // make steps positive since we already set that we would move downward by setting dirPin
  } else {
    digitalWrite(dirPin, HIGH);
  }

  for(int i = 0; i < steps * 8; i++){  // 8 is microstep amount
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(100);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(100);
  }
}
