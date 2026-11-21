/*
  MediGuide - ESP32 code
  ----------------------
  - Connects to Wi-Fi and to ROS (rosserial over TCP, port 11411)
  - Gets directions from ROS, e.g. "F150,R90,F400,L90,F100,U"
        F<cm>  forward      R<deg> turn right
        L<deg> turn left    U      turn around (180)
  - Follows them one by one (no line on the floor)
  - Stops and waits if the front IR sensor sees something
  - Opens / closes the tray lid with the SG90 servo
  - Sends the Ward and Return button presses to ROS

  ROS topics:
    publish   /robot/button    std_msgs/String   "ward" or "return"
    publish   /robot/arrived   std_msgs/Bool
    publish   /robot/obstacle  std_msgs/Bool
    subscribe /robot/go        std_msgs/String   directions
    subscribe /robot/lid       std_msgs/Bool     true = open

  Libraries (Arduino IDE -> Library Manager):
    - "Rosserial Arduino Library" by Michael Ferguson
    - "ESP32Servo" by Kevin Harrington
  Board: "ESP32 Dev Module"
*/

#include <WiFi.h>
#define ROSSERIAL_ARDUINO_TCP
#include <ros.h>
#include <std_msgs/String.h>
#include <std_msgs/Bool.h>
#include <ESP32Servo.h>

// ---------------- CHANGE THESE ----------------
const char* WIFI_NAME     = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
IPAddress   ROS_PC(192, 168, 1, 100);   // IP of the Ubuntu computer (hostname -I)
const uint16_t ROS_PORT = 11411;

// Calibration: measure these on your floor (see README)
const float CM_PER_SECOND   = 30.0;   // how many cm the robot moves in 1 second
const float MS_PER_90_DEG   = 700.0;  // how many ms the robot takes to turn 90 degrees
// ----------------------------------------------

// Motor driver (L298N)
const int ENA = 14, IN1 = 27, IN2 = 26;   // left motors
const int ENB = 32, IN3 = 25, IN4 = 33;   // right motors

// Sensor, servo, buttons, LED
const int IR_FRONT   = 34;     // obstacle sensor (FC-51)
const int SERVO_PIN  = 13;
const int BTN_WARD   = 18;
const int BTN_RETURN = 19;
const int LED        = 2;

// Most FC-51 modules give LOW when something is in front.
// If yours works the other way, change LOW to HIGH.
const int OBSTACLE_SEEN = LOW;

// Speeds (0 - 255). If the robot does not go straight, make LEFT and RIGHT a bit different.
const int SPEED_LEFT  = 150;
const int SPEED_RIGHT = 150;
const int SPEED_TURN  = 150;

// Servo angles
const int LID_OPEN_ANGLE  = 90;
const int LID_CLOSE_ANGLE = 0;

// ---------------- ROS ----------------
ros::NodeHandle nh;
std_msgs::String button_msg;
std_msgs::Bool   arrived_msg;
std_msgs::Bool   obstacle_msg;
ros::Publisher button_pub("/robot/button", &button_msg);
ros::Publisher arrived_pub("/robot/arrived", &arrived_msg);
ros::Publisher obstacle_pub("/robot/obstacle", &obstacle_msg);

Servo lid;

// ---------------- Route ----------------
const int MAX_STEPS = 20;
char  step_type[MAX_STEPS];     // 'F', 'L', 'R'
unsigned long step_ms[MAX_STEPS];
int   step_count = 0;
int   step_now = -1;            // -1 = not moving
unsigned long step_left_ms = 0; // time left in this step
unsigned long last_tick = 0;
bool  obstacle_now = false;
unsigned long last_press = 0;

// ---------------- Motors ----------------
void setMotors(int left, int right) {
  digitalWrite(IN1, left >= 0 ? HIGH : LOW);
  digitalWrite(IN2, left >= 0 ? LOW : HIGH);
  digitalWrite(IN3, right >= 0 ? HIGH : LOW);
  digitalWrite(IN4, right >= 0 ? LOW : HIGH);
  analogWrite(ENA, abs(left));
  analogWrite(ENB, abs(right));
}

void stopMotors() {
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
}

void driveStep(char type) {
  if (type == 'F')      setMotors(SPEED_LEFT, SPEED_RIGHT);
  else if (type == 'R') setMotors(SPEED_TURN, -SPEED_TURN);
  else if (type == 'L') setMotors(-SPEED_TURN, SPEED_TURN);
}

// ---------------- Read the directions ----------------
// "F150,R90,F400,L90,F100,U"  ->  list of steps with times
void loadRoute(const char* text) {
  step_count = 0;
  const char* p = text;
  while (*p != '\0' && step_count < MAX_STEPS) {
    char type = *p++;
    float value = atof(p);
    while (*p != '\0' && *p != ',') p++;
    if (*p == ',') p++;

    if (type == 'F') {
      step_type[step_count] = 'F';
      step_ms[step_count] = (unsigned long)(value / CM_PER_SECOND * 1000.0);
    } else if (type == 'R' || type == 'L') {
      step_type[step_count] = type;
      step_ms[step_count] = (unsigned long)(value / 90.0 * MS_PER_90_DEG);
    } else if (type == 'U') {
      step_type[step_count] = 'R';
      step_ms[step_count] = (unsigned long)(2.0 * MS_PER_90_DEG);
    } else {
      continue;   // unknown letter, skip it
    }
    step_count++;
  }
}

void startStep(int i) {
  step_now = i;
  step_left_ms = step_ms[i];
  last_tick = millis();
  if (!obstacle_now) driveStep(step_type[i]);
}

void finishRoute() {
  stopMotors();
  step_now = -1;
  digitalWrite(LED, LOW);
  arrived_msg.data = true;
  arrived_pub.publish(&arrived_msg);
}

// Runs every loop while the robot is moving
void runRoute() {
  unsigned long now = millis();
  unsigned long passed = now - last_tick;
  last_tick = now;

  // Obstacle check: stop the clock while something is in front
  bool obs = digitalRead(IR_FRONT) == OBSTACLE_SEEN && step_type[step_now] == 'F';
  if (obs != obstacle_now) {
    obstacle_now = obs;
    obstacle_msg.data = obs;
    obstacle_pub.publish(&obstacle_msg);
    if (obs) stopMotors();
    else     driveStep(step_type[step_now]);
  }
  if (obstacle_now) return;

  if (passed >= step_left_ms) {
    stopMotors();
    delay(200);   // short pause between steps
    last_tick = millis();
    if (step_now + 1 < step_count) startStep(step_now + 1);
    else finishRoute();
  } else {
    step_left_ms -= passed;
  }
}

// ---------------- ROS callbacks ----------------
void onGo(const std_msgs::String& msg) {
  loadRoute(msg.data);
  if (step_count == 0) return;
  obstacle_now = false;
  digitalWrite(LED, HIGH);
  startStep(0);
}

void onLid(const std_msgs::Bool& msg) {
  lid.write(msg.data ? LID_OPEN_ANGLE : LID_CLOSE_ANGLE);
}

ros::Subscriber<std_msgs::String> go_sub("/robot/go", &onGo);
ros::Subscriber<std_msgs::Bool>   lid_sub("/robot/lid", &onLid);

// ---------------- Buttons ----------------
void readButtons() {
  if (millis() - last_press < 400) return;   // simple debounce
  const char* pressed = NULL;
  if (digitalRead(BTN_WARD) == LOW)   pressed = "ward";
  if (digitalRead(BTN_RETURN) == LOW) pressed = "return";
  if (pressed != NULL) {
    button_msg.data = pressed;
    button_pub.publish(&button_msg);
    last_press = millis();
  }
}

// ---------------- Setup / loop ----------------
void setup() {
  pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);
  pinMode(ENA, OUTPUT); pinMode(ENB, OUTPUT);
  pinMode(IR_FRONT, INPUT);
  pinMode(BTN_WARD, INPUT_PULLUP);
  pinMode(BTN_RETURN, INPUT_PULLUP);
  pinMode(LED, OUTPUT);
  stopMotors();

  lid.attach(SERVO_PIN);
  lid.write(LID_OPEN_ANGLE);

  Serial.begin(115200);
  WiFi.begin(WIFI_NAME, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    digitalWrite(LED, !digitalRead(LED));
  }
  Serial.print("\nConnected. ESP32 IP: ");
  Serial.println(WiFi.localIP());
  digitalWrite(LED, LOW);

  nh.getHardware()->setConnection(ROS_PC, ROS_PORT);
  nh.initNode();
  nh.advertise(button_pub);
  nh.advertise(arrived_pub);
  nh.advertise(obstacle_pub);
  nh.subscribe(go_sub);
  nh.subscribe(lid_sub);
}

void loop() {
  if (!nh.connected() && step_now >= 0) {
    stopMotors();          // lost ROS: stop and wait
    step_now = -1;
  }
  readButtons();
  if (step_now >= 0) runRoute();
  nh.spinOnce();
  delay(5);
}
