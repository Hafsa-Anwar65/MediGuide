# MediGuide – Run karne ki guide

**Kaam:** Robot ward mein khada hai. Nurse parchi tray mein rakh kar **Ward** button dabati hai. Robot pharmacy jata hai. Pharmacist parchi parh kar dawai rakhta hai aur **Return** dabata hai. Robot wapas ward aa jata hai.

- Sirf **ek ward** aur **ek pharmacy**
- Floor par **koi line nahi**. Robot pehle se likhe directions par chalta hai (seedha, right, left)

```
MediGuide/
├── setup.sh                 ← sab kuch install aur build karta hai
├── README.md                ← ye guide
├── mediguide/               ← ROS package
│   ├── scripts/
│   │   ├── deliverymanager.py   (robot ka dimagh, state machine)
│   │   ├── routeserver.py       (custom service: raasta aur directions)
│   │   ├── stationmarkers.py    (RViz mein Ward/Pharmacy ke naam)
│   │   └── nursepanel.py        (simulation ke liye keyboard buttons)
│   ├── srv/GetRoute.srv     ← custom service
│   ├── config/stations.yaml ← directions aur locations (yahan badlein)
│   ├── config/mediguide.rviz
│   ├── launch/
│   ├── worlds/hospital.world← Gazebo hospital
│   ├── maps/                ← hospital ka map (AMCL ke liye)
│   └── tools/makehospital.py
└── esp32/MediGuideESP32/MediGuideESP32.ino ← ESP32 ka code
```

---

## PART 1: Setup / Update

Naya version aane par bhi yahi karna hai:

```bash
cd ~/Downloads/MediGuide
bash setup.sh
```
"DONE" aaye to terminal band karke naya kholein.

---

## PART 2: Gazebo simulation

**Terminal 1:**
```bash
roslaunch mediguide simulation.launch
```

**Terminal 2:**
```bash
rosrun mediguide nursepanel.py
```

| Key | Matlab |
|---|---|
| `w` | Nurse ne **Ward** button dabaya → robot pharmacy jayega |
| `r` | Pharmacist ne **Return** dabaya → robot ward wapas aayega |
| `q` | Band karein |

Simulation mein robot khud raasta dhoondta hai (AMCL + move_base). RViz mein neeli line planned path hai.

---

## PART 3: gmapping se map banana (demo ke liye)

```bash
roslaunch mediguide mapping.launch                          # Terminal 1
rosrun teleop_twist_keyboard teleop_twist_keyboard.py       # Terminal 2
rosrun map_server map_saver -f ~/hospital_gmapping          # Terminal 3, map save
```
Teleop: `i` aage, `,` peeche, `j` / `l` ghoomna, `k` rukna.

---

## PART 4: Viva ke liye commands

```bash
rosrun rqt_graph rqt_graph                    # nodes aur topics ka diagram
rostopic echo /robot/status                   # robot kya kar raha hai
rosservice call /getroute ward pharmacy      # custom service test
rosparam get /route_to_pharmacy               # YAML se aaye directions
```

---

## PART 5: Asli robot (ESP32)

### Directions kaise likhni hain

`mediguide/config/stations.yaml` mein:
```yaml
route_to_pharmacy: ["F150", "R90", "F400", "L90", "F100"]
```
| Code | Matlab |
|---|---|
| `F150` | 150 cm seedha |
| `R90` | 90° right mudo |
| `L90` | 90° left mudo |

Ward se pharmacy tak ka asli raasta naap kar ye numbers badlein. **Wapsi ka raasta khud ban jata hai** (ulta order, right ↔ left). Har trip ke aakhir mein robot U-turn leta hai taake agli trip ke liye tayyar ho.

YAML badalne ke baad dobara `bash setup.sh` chalayein.

### Wiring

| ESP32 pin | Kahan jayega |
|---|---|
| GPIO 14 | L298N **ENA** (jumper hata dein) |
| GPIO 27 | L298N IN1 |
| GPIO 26 | L298N IN2 |
| GPIO 32 | L298N **ENB** (jumper hata dein) |
| GPIO 25 | L298N IN3 |
| GPIO 33 | L298N IN4 |
| GPIO 34 | Front IR obstacle sensor – OUT |
| GPIO 13 | SG90 servo – signal (orange) |
| GPIO 18 | Ward button (doosra sira GND) |
| GPIO 19 | Return button (doosra sira GND) |
| 5V / VIN | Buck converter 5V output |
| GND | Buck converter GND **aur** L298N GND (common ground zaroori) |

- Left motors → OUT1/OUT2, right motors → OUT3/OUT4
- Battery 12V → L298N 12V aur buck converter input
- **Buck converter ko pehle multimeter se 5V par set karein**, phir ESP32 lagayein
- Servo ka red taar buck ke 5V se; **IR sensor ka VCC ESP32 ke 3V3 pin se** (5V nahi), GND sab common

### Calibration (zaroori)

Robot ke motors mein encoder nahi, isliye distance **time** se nikalta hai. Code mein ye do numbers apne robot ke hisaab se set karein:
```cpp
const float CM_PER_SECOND = 30.0;   // 1 second mein robot kitne cm chalta hai
const float MS_PER_90_DEG = 700.0;  // 90° mudne mein kitne ms lagte hain
```
1. YAML mein route sirf `["F100"]` rakhein. Robot jitna chala use naapein. Agar 100 ki jagah 80 cm chala, to `CM_PER_SECOND` ko 30 × 80/100 = 24 kar dein.
2. Phir `["R90"]` se check karein. Kam mude to `MS_PER_90_DEG` badhayein, zyada mude to kam karein.
3. Robot seedha na chale to `SPEED_LEFT` / `SPEED_RIGHT` mein thoda farq rakhein.

Battery kam hone par robot dheema ho jata hai, isliye demo se pehle battery full rakhein.

### ESP32 mein code daalna (Windows ka Arduino IDE)

1. Boards Manager → "esp32" by Espressif (**version 2.0.x** behtar)
2. Library Manager → **Rosserial Arduino Library** (Michael Ferguson) aur **ESP32Servo** (Kevin Harrington)
3. `MediGuideESP32.ino` mein badlein: `WIFI_NAME`, `WIFI_PASSWORD`, aur `ROS_PC` (VM mein `hostname -I` se IP)
4. Board: **ESP32 Dev Module** → Upload

### VM network (sirf asli robot ke liye)

VM band karein → VirtualBox **Settings → Network → Adapter 1 → Bridged Adapter** → apna Wi-Fi adapter → OK.

### Chalana

```bash
roslaunch mediguide realrobot.launch
```
ESP32 on karein. Connection ban jaye to robot ke buttons dabayein.

---

## Masle aur hal

| Masla | Hal |
|---|---|
| Gazebo band ho jata hai ya kaali screen | VirtualBox → Display → **3D Acceleration** on/off kar ke dekhein, ya pehle `export LIBGL_ALWAYS_SOFTWARE=1` |
| Simulation slow | VM ko 4 GB+ RAM, 2+ CPU; ya `roslaunch mediguide simulation.launch gui:=false` |
| `package 'mediguide' not found` | Naya terminal kholein |
| Obstacle sensor ulta kaam kare | Code mein `OBSTACLE_SEEN = LOW` ko `HIGH` karein |
| ESP32 compile error | ESP32 board version 2.0.x, phir screenshot bhejein |
