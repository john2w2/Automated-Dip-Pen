
#define dirPin 4
#define stepPin 5

int microstep = 8;
void setup() {
  // put your setup code here, to run once:
  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);

  Serial.begin(115200);
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

  for(int i = 0; i < steps * microstep; i++){  
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(500);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(500);
  }
}

void loop() {
while (!Serial.available()){
    // this waits for something to be written into serial until program execution continues
  }

  String line = Serial.readStringUntil('\r');
  int spaceIndex = line.indexOf(" ");
  String cmd;
  String arg; 
  
  if (spaceIndex != -1) {
    cmd = line.substring(0, spaceIndex);
    arg = line.substring(spaceIndex, line.length());
  } else {
    cmd = line;
    arg = "N/A";
  }
  takeSteps(cmd.toInt());
}
