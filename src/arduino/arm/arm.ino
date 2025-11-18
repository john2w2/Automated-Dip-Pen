// arduino outputs
#define stepPin1 5 // motor 1
#define dirPin1 7  // motor 1
#define stepPin2 8 // motor 2
#define dirPin2 9  // motor 2

#define endstop_1 2 // Optical endstop for Motor 1
#define endstop_2 3 // Optical endstop for Motor 2

const int PULSE_WIDTH = 50; // microseconds
const int STEP_DELAY_UP = 100;   // faster  
const int STEP_DELAY_DOWN = 100; // slower

int microstep = 8;
// position in number of steps from top limit switch
int zposition = 12345; // represents some uninitialized value (actual value is in range [0, -43400ish). depends on the pen 
                       // The range depends on how high limit switch is, but will always be negative since
                       // we are moving below the top switch 

void setup() {
  // Motor control pins
  pinMode(stepPin1, OUTPUT);
  pinMode(dirPin1, OUTPUT);
  pinMode(stepPin2, OUTPUT);
  pinMode(dirPin2, OUTPUT);

  // Endstop pins (optical, active LOW with pull-up)
  pinMode(endstop_1, INPUT_PULLUP);
  pinMode(endstop_2, INPUT_PULLUP);

  Serial.begin(115200);
  Serial.println("ready");
}

// replacement for library command to take a step
// also adjusts steps for a microstep factor of 1/8 (so issuing command for 200 steps still does one revolution)
// void takeSteps(int steps){
//   if (steps < 0){
//     // negative steps is dir == LOW
//     // writing low to dirPin means steps will be taken downward
//     digitalWrite(dirPin1, LOW);
//     digitalWrite(dirPin2, LOW);
//     steps = -steps; // make steps positive since we already set that we would move downward by setting dirPin
//   } else {
//     digitalWrite(dirPin1, HIGH);
//     digitalWrite(dirPin2, HIGH);
//   }

//   for(int i = 0; i < steps * microstep; i++){  
//     digitalWrite(stepPin, HIGH);
//     delayMicroseconds(500); // Pulse Width (adjustable)
//     digitalWrite(stepPin, LOW);
//     delayMicroseconds(500); // Step interval
//   }
// }

// Pulse one step 
void pulseMotor(int stepPin, bool goingup) {
  int stepDelay = goingup ? STEP_DELAY_UP : STEP_DELAY_DOWN;
  for (int i = 0; i < microstep; i++) {
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(PULSE_WIDTH);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(stepDelay);
  }
}

// moves the z arm upwards until it triggers the top optical endstop, then
// backs off until optical endstop is no longer triggered. Saves final
// position internally as position 0
void calibrate() {
  // Set both motors to move UP toward endstops
  digitalWrite(dirPin1, HIGH);
  digitalWrite(dirPin2, HIGH);

  bool motor1Done = false;
  bool motor2Done = false;

  // Keep looping until both motors are homed
  while (!motor1Done || !motor2Done) {

    // Motor 1 movement
    if (!motor1Done) {
      if (digitalRead(endstop_1) == HIGH) { // HIGH = triggered
        if (checkInterrupted()) return; // exit if interrupted
        motor1Done = true;
        Serial.println("Motor 1 homed.");
      } else {
        pulseMotor(stepPin1, true); // Pulse motor 1 up
        pulseMotor(stepPin2, true); // Pulse motor 2 up
      }
    }

    // Motor 2 movement
    if (!motor2Done) {
      if (digitalRead(endstop_2) == HIGH) { // HIGH = triggered
        if (checkInterrupted()) return; // Exit if interrupted
        motor2Done = true;
        Serial.println("Motor 2 homed.");
      } else {
        pulseMotor(stepPin1, true); // Pulse motor 1 up
        pulseMotor(stepPin2, true); // Pulse motor 2 up
      }
    }
  }

  digitalWrite(dirPin1, LOW);
  digitalWrite(dirPin2, LOW);
  for (int i = 0; i < 200; i++){
    if (checkInterrupted()) return; // exit if interrupted
    pulseMotor(stepPin1, false);
    pulseMotor(stepPin2, false);
  }

  zposition = 0;

  // move up one step at a time until beam is blocked
  // digitalWrite(dirPin, HIGH); // move up towards optical endstop
  // while(digitalRead(endstopPin) == LOW){
  //   if (checkInterrupted()) return; // should exit without running any code below
  //   takeSteps(1);
  // }

  // // move down until optical endstop is unblocked, then save that position as 0
  // digitalWrite(dirPin, LOW);
  // while(digitalRead(endstopPin) == HIGH){
  //   if (checkInterrupted()) return; // should exit without running any code below
  //   takeSteps(-1);
  // }
}

// moves the z arm to pos 
// top is 0, everything below is negative
// If everything is wired correctly, the motor will not move above 0. 
// It will ignore commands that tell it to move above 0 rather than moving to 0
// void moveToZ(int pos){
//   if (pos > 0 || zposition > 0) return; // zposition > 0 when not calibrated
//   int difference = pos - zposition; // 
//   int takenSteps = 0;
//   int dir = 1;
//   if (difference < 0) dir = -1;

//   // loop until we've taken as many steps as we needed
//   // looping one step at a time also allows us to 
//   while(abs(takenSteps) < abs(difference)){
//     bottomLimit.loop();
//     topLimit.loop();
//     int bottomState = bottomLimit.getState();
//     int topState = topLimit.getState();
//     if (dir == -1){ // moving down
//       if (bottomState == HIGH){
//         // Serial.println("bottom hit");
//         break;
//       }
//     } else { // moving up
//       if (topState == HIGH){
//         // Serial.println("top hit");
//         break;
//       }
//     }
//     if (checkInterrupted()) break;
//     takeSteps(dir * 1);
//     takenSteps += dir * 1;
//   }
//   zposition += takenSteps;
// }

void moveToZ(int pos) {
  // Prevent movement if not yet calibrated (zposition > 0 means calibrated)
  if (zposition > 0 || pos > 0) return;

  int difference = pos - zposition;
  int takenSteps = 0;
  int dir = (difference < 0) ? -1 : 1;

  // For pulseMotor function
  bool goingUp = (dir == 1);

  // Set direction
  digitalWrite(dirPin1, goingUp ? HIGH : LOW);
  digitalWrite(dirPin2, goingUp ? HIGH : LOW);

  while (abs(takenSteps) < abs(difference)) {
    // If moving upward and endstop is hit (beam blocked), stop
    if (dir == 1 && digitalRead(endstop_1) == HIGH && digitalRead(endstop_2) == HIGH) {
      break;
    }

    if (checkInterrupted()) break;

    pulseMotor(stepPin1, goingUp);
    pulseMotor(stepPin2, goingUp);
    takenSteps += dir;
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

// void takeStepsY(int steps){
//   if (steps < 0){
//     // negative steps is dir == LOW
//     // writing low to dirPin means steps will be taken downward
//     digitalWrite(yDir, LOW);
//     steps = steps * -1; // make steps positive since we already set that we would move downward by setting dirPin
//   } else {
//     digitalWrite(yDir, HIGH);
//   }

//   for(int i = 0; i < steps * microstep; i++){  
//     digitalWrite(yStep, HIGH);
//     delayMicroseconds(500);
//     digitalWrite(yStep, LOW);
//     delayMicroseconds(500);
//   }
// }

// relative Y axis move, does not check if any limit switches are hit
// It is capable of being interrupted
// void moveByY(int steps){
//   int dir = 1;
//   if (steps < 0) {
//     dir = -1;
//     steps = steps * -1;
//   } else {
     
//   }
  
//   for (int i = 0; i < steps; i++){
//     if (checkInterrupted()) break;
//     takeStepsY(1 * dir);
//   }
// }

// waits for serial commands, then calls the appropriate function for each command
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
  dispatch(cmd, arg);
}


// Interprets the serial command, dispatching it to the appropriate function.
// All movement related commands will emit an "idle" signal when finished.
// If a command isn't recognized, the arduino does nothing
void dispatch(String cmd, String arg){
  if (cmd.equals("moveToZAbsolute")) {
    int steps = arg.toInt();
    moveToZ(steps);
    Serial.println("idle");
  } else if (cmd.equals("getZPosition")) {
    getZPosition();
  } else if (cmd.equals("calibrateOrigin")) {
    calibrate();
    Serial.println("idle");}
  // } else if (cmd.equals("moveByY")) {
  //   int steps = arg.toInt();
  //   moveByY(steps);
  //   Serial.println("idle");
  // }
}
