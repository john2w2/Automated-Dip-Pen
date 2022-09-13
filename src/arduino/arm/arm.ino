#include <ezButton.h>

#define dirPin 4
#define stepPin 5

#define yDir 2
#define yStep 3
int microstep = 8;

ezButton topLimit(12);
ezButton bottomLimit(13);

// position in number of steps from top limit switch
int zposition = 12345; // represents some uninitialized value (actual value is in range [0, -5000ish). Right now the lowest we have it go is -5200

void setup() {
  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);
  pinMode(yDir, OUTPUT);
  pinMode(yStep, OUTPUT);
  Serial.begin(115200);
  topLimit.setDebounceTime(50);
  bottomLimit.setDebounceTime(50);
  delay(1000); // some delay so stepper drivers have time to wake up (I saw this online IDK what it means but I think it's important)
  Serial.println("arduino ready");
}

// replacement for library command to take a step
// also adjusts steps for a microstep factor of 1/8 (so issuing command for 200 steps still does one revolution)
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
    delayMicroseconds(250);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(250);
  }
}

// moves the z arm upwards until it hits the top limit switch, then
// backs off until limit switch is no longer pressed. Saves final
// position internally as position 0
void calibrate() {
  topLimit.loop();
  int topState = topLimit.getState();
  
  // move up one step at a time until top limit is hit
  while(topState == LOW){
    if (checkInterrupted()) return; // should exit without running any code below
    takeSteps(1);
    topLimit.loop();
    topState = topLimit.getState();
  }

  // move down until top switch is untouched, then save that position as 0
  topLimit.loop();
  topState = topLimit.getState();
  
  while(topState == HIGH){
    if (checkInterrupted()) return; // should exit without running any code below
    takeSteps(-1);
    topLimit.loop();
    topState = topLimit.getState();
  }
  zposition = 0;
}

// moves the z arm to pos 
// top is 0, everything below is negative
void moveToZ(int pos){
  if (pos > 0 || zposition > 0) return; // zposition > 0 when not calibrated
  int difference = pos - zposition; // 
  int takenSteps = 0;
  int dir = 1;
  if (difference < 0) dir = -1;

  // loop until we've taken as many steps as we needed
  // looping one step at a time also allows us to 
  while(abs(takenSteps) < abs(difference)){
    bottomLimit.loop();
    topLimit.loop();
    int bottomState = bottomLimit.getState();
    int topState = topLimit.getState();
    if (dir == -1){ // moving down
      if (bottomState == HIGH){
        // Serial.println("bottom hit");
        break;
      }
    } else { // moving up
      if (topState == HIGH){
        // Serial.println("top hit");
        break;
      }
    }
    if (checkInterrupted()) break;
    takeSteps(dir * 1);
    takenSteps += dir * 1;
  }
  zposition += takenSteps;
}

// checks if an interrupt command has been issued from serial
// returns true if interrupted
// warning: consumes a buffered line from serial, potentially deleting a command
//    this shouldn't be a big deal if arm is controlled by only 1 thread
boolean checkInterrupted(){
  if (Serial.available()){
      String line = Serial.readStringUntil('\r');
      if (line.equals("INTERRUPT")) return true;
      else return false;
  } else{
    return false;
  }
}

void getZPosition(){
  Serial.println(zposition);
}

void takeStepsY(int steps){
  if (steps < 0){
    // negative steps is dir == LOW
    // writing low to dirPin means steps will be taken downward
    digitalWrite(yDir, LOW);
    steps = steps * -1; // make steps positive since we already set that we would move downward by setting dirPin
  } else {
    digitalWrite(yDir, HIGH);
  }

  for(int i = 0; i < steps * microstep; i++){  
    digitalWrite(yStep, HIGH);
    delayMicroseconds(500);
    digitalWrite(yStep, LOW);
    delayMicroseconds(500);
  }
}

// relative Y axis move, does not check if any limit switches are hit
// It is capable of being interrupted
void moveByY(int steps){
  int dir = 1;
  if (steps < 0) {
    dir = -1;
    steps = steps * -1;
  } else {
     
  }
  
  for (int i = 0; i < steps; i++){
    if (checkInterrupted()) break;
    takeStepsY(1 * dir);
  }
}

void loop() {
  bottomLimit.loop();
  topLimit.loop();
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
  dispatch(cmd, arg);
}

// interprets the serial command, dispatching it to the appropriate function
// all movement related commands will emit an "idle" signal when finished, handled here
void dispatch(String cmd, String arg){
  if (cmd.equals("moveToZAbsolute")) {
    int steps = arg.toInt();
    moveToZ(steps);
    Serial.println("idle");
  } else if (cmd.equals("getZPosition")) {
    getZPosition();
  } else if (cmd.equals("calibrateOrigin")) {
    calibrate();
    Serial.println("idle");
  } else if (cmd.equals("moveByY")) {
    int steps = arg.toInt();
    moveByY(steps);
    Serial.println("idle");
  }
}
