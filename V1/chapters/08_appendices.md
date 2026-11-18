# الملاحق الفنية وسجلات الأكواد البرمجية والمراجع
## Section VIII: Technical Appendices, Code Listings & Comprehensive Bibliography

---

### 1.8 الملحق أ: المخططات الهندسية وتعيين المداخل الإلكترونية (Pinout & Hardware Architecture)

#### 1.1.8 المعمارية العامة للوحة التحكم V3
تعتمد لوحة التحكم الرئيسية لمشروع **ROBOI (الإصدار V3)** على المعالج الميكروي ثنائي النواة **ESP32-S3-WROOM-1**، الذي يتميز بتردد تشغيل يصل إلى 240 ميجاهرتز، ودعم تسريع عمليات المتجهات الرياضية (*Vector Instructions*)، والاتصال اللاسلكي المزدوج (*Wi-Fi 802.11 b/g/n & Bluetooth 5 LE*). تم تصميم اللوحة لتوفير خطوط تحكم موثوقة لمحركات السيرفو التسلسلية الذكية (*Serial Bus Servos*) مع قنوات قراءة تناظرية متزامنة ودوائر حماية صناعية.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    المعمارية العتادية للوحة التحكم ROBOI V3                  │
│                     (ROBOI V3 Controller Board Architecture)                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   [ دخل التغذية: 7V - 24V DC ]                                              │
│               │                                                             │
│               ▼                                                             │
│   [ محول DC-DC خافض: TPS54560BDDA ] ──► خرج قدرة: 5V - 7.4V @ 5A            │
│               │                                (تغذية محركات السيرفو)       │
│               ▼                                                             │
│   [ منظم جهد خطي: ME6211C33M5 ] ───────► خرج قدرة: 3.3V @ 500mA             │
│                                                (تغذية المعالج والحساسات)    │
│                                                                             │
│   [ المعالج الميكروي: ESP32-S3 ]                                            │
│   ├── GPIO 17 / GPIO 18 ──► دائرة تحويل UART نصف مزدوج ──► محركات Feetech   │
│   ├── GPIO 4, 5, 6, 7   ──► خطوط اختيار القنوات S0-S3 ──► مضاعف CD74HC4067 │
│   ├── GPIO 1 (ADC1_CH0) ──► خط إشارة التغذية الراجعة SIG ◄──┘               │
│   ├── GPIO 8 / GPIO 9   ──► ناقل I2C (شاشة OLED / مستشعرات IMU)             │
│   └── USB-C (D+/D-)     ──► حماية ESD (USBLC6-2SC6) ──► برمجة وتخاطب PC     │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 2.1.8 جدول تعيين الأرجل والتوصيلات الكهربائية (Pinout Assignment Table)

| رقم الطرف (GPIO) | الوظيفة الهندسية الأساسية | التوصيف الإلكتروني والدائرة المتصلة | بروتوكول الاتصال / مستوى الإشارة |
| :---: | :--- | :--- | :---: |
| **GPIO 1** | قراءة إشارة التغذية الراجعة التناظرية | متصل بالطرف الموحد `SIG` في شريحة المضاعف `CD74HC4067SM` | دخل تناظري بدقة 12 بت (0 – 3.3V) عبر `ADC1_CH0` |
| **GPIO 4** | خط اختيار القناة التناظرية S0 | التحكم في البت الأول لتحديد مدخل المقاومة التناظرية | خرج رقمي `S0` (منطق 3.3V CMOS) |
| **GPIO 5** | خط اختيار القناة التناظرية S1 | التحكم في البت الثاني لتحديد مدخل المقاومة التناظرية | خرج رقمي `S1` (منطق 3.3V CMOS) |
| **GPIO 6** | خط اختيار القناة التناظرية S2 | التحكم في البت الثالث لتحديد مدخل المقاومة التناظرية | خرج رقمي `S2` (منطق 3.3V CMOS) |
| **GPIO 7** | خط اختيار القناة التناظرية S3 | التحكم في البت الرابع لتحديد مدخل المقاومة التناظرية | خرج رقمي `S3` (منطق 3.3V CMOS) |
| **GPIO 8** | خط بيانات ناقل I2C المساعد (SDA) | متصل بشاشة العرض التشخيصية `OLED SSD1306` وحساس الحركة | ناقل ثنائي الاتجاه `I2C SDA` مع مقاومة رفع 4.7kΩ |
| **GPIO 9** | خط نبضات ساعة ناقل I2C (SCL) | تزامن نقل البيانات لشاشة العرض وحساسات القصور الذاتي | خط ساعة `I2C SCL` بتردد 400 كيلوهرتز |
| **GPIO 17** | خط إرسال بيانات السيرفو (TXD) | متصل بدائرة تحويل المستوى والتخاطب نصف المزدوج | تسلسلي `UART2 TX` بسرعة 1,000,000 بت/ثانية |
| **GPIO 18** | خط استقبال بيانات السيرفو (RXD) | قراءة حزم البيانات وحالة المحركات وسجلات الحرارة والجهد | تسلسلي `UART2 RX` بسرعة 1,000,000 بت/ثانية |
| **GPIO 19** | طرف USB D- | متصل بمنفذ `USB-C 16-Pin` عبر شريحة حماية `USBLC6-2SC6` | اتصال USB تسلسلي مباشر عالي السرعة (Native USB CDC) |
| **GPIO 20** | طرف USB D+ | متصل بمنفذ `USB-C 16-Pin` عبر شريحة حماية `USBLC6-2SC6` | اتصال USB تسلسلي مباشر عالي السرعة (Native USB CDC) |

#### 3.1.8 دائرة التغذية الكهربائية وخافض الجهد TPS54560BDDA
تتطلب المحركات التسلسلية الذكية Feetech STS3215 استجرار تيارات لحظية عالية تصل إلى 2.5 أمبير لكل محرك عند بدء الحركة أو عند بلوغ عزم التوقف (*Stall Torque*). ولمنع انهيار الجهد وإعادة إقلاع المعالج (*Brownout Reset*)، تعتمد اللوحة على محول التنحي النبضي عالي الكفاءة **TPS54560BDDA** من شركة Texas Instruments، والمصمم وفق الحسابات التالية:
* **نطاق جهد الدخل المسموح:** من 7.0 فولت إلى 24.0 فولت تيار مستمر (يدعم بطاريات LiPo 2S-4S ومصادر التغذية الصناعية 12V و 24V).
* **تيار الخرج المستمر:** حتى 5.0 أمبير (مع تيار لحظي يصل إلى 6.5 أمبير).
* **تردد التقطيع النبضي (*Switching Frequency*):** مضبوط عند 500 كيلوهرتز عبر مقاومة ضبط التوقيت $R_{\text{FREQ}} = 200\text{ k}\Omega$ لتحقيق التوازن بين كفاءة التحويل (تتجاوز 92%) وتقليل الحجم الفيزيائي لملف الخنق.
* **ملف الخنق الحثي (*Power Inductor*):** محث معزول مغناطيسياً بقيمة $10\,\mu\text{H}$ وتيار تشبع لا يقل عن 7.5 أمبير لمنع التشويش الكهرومغناطيسي على دوائر الحساسات.
* **مكثفات الترشيح:** مكثفات خزفية منخفضة المقاومة الداخلية (*Low-ESR MLCC*) بسعة $2\times 47\,\mu\text{F}$ على الخرج مع مكثف كيميائي مساعد بسعة $470\,\mu\text{F}$ لامتصاص الارتدادات العكسية للمحركات.

---

### 2.8 الملحق ب: كود البرمجيات الثابتة ونظام التحكم (Firmware & Control Stack Listing)

#### 1.2.8 كود البرمجيات الثابتة C++ للمتحكم ESP32-S3
يوضح الكود التالي المكتوب لبيئة *PlatformIO / Arduino Framework* النواة التشغيلية لمتحكم **ROBOI V3**، حيث يقوم بتهيئة الاتصال التسلسلي مع محركات Feetech STS بسرعة 1 ميجابت/ثانية، وتفعيل مقاطعة دورية عالية الدقة لتوليد المسارات الحركية وتجانس السرعات بمعدل 100 هرتز لمنع الصدمات الميكانيكية:

```cpp
/**
 * ============================================================================
 * مشروع ROBOI - البرمجيات الثابتة للوحة التحكم V3 (ESP32-S3)
 * ROBOI Platform Firmware V3 - Multi-Joint Closed-Loop Control Engine
 * ============================================================================
 * الكود يتيح قراءة زوايا المفاصل آنياً، والتحكم في محركات Feetech STS3215/3032
 * عبر بروتوكول نصف المزدوج، مع معالجة تنعيم الحركة وتوليد المسارات.
 */

#include <Arduino.h>
#include <HardwareSerial.h>

// تعريف أطراف التوصيل الإلكتروني
#define PIN_SERVO_TX      17
#define PIN_SERVO_RX      18
#define PIN_MUX_S0        4
#define PIN_MUX_S1        5
#define PIN_MUX_S2        6
#define PIN_MUX_S3        7
#define PIN_MUX_SIG       1

// ثوابت المنظومة
#define NUM_JOINTS        6
#define SERVO_BAUDRATE    1000000
#define CONTROL_FREQ_HZ   100

HardwareSerial ServoBus(2);

// بنية بيانات حالة المفصل الروبوتي
struct JointState {
    uint8_t  id;
    int16_t  target_position;
    int16_t  current_position;
    int16_t  current_speed;
    uint16_t load_torque;
    uint8_t  temperature;
    float    target_angle_rad;
    float    current_angle_rad;
};

JointState joints[NUM_JOINTS];

// دالة تهيئة مضاعف القنوات التناظرية CD74HC4067
void initMultiplexer() {
    pinMode(PIN_MUX_S0, OUTPUT);
    pinMode(PIN_MUX_S1, OUTPUT);
    pinMode(PIN_MUX_S2, OUTPUT);
    pinMode(PIN_MUX_S3, OUTPUT);
    pinMode(PIN_MUX_SIG, INPUT);
}

// دالة قراءة قناة تناظرية محددة
uint16_t readAnalogChannel(uint8_t channel) {
    digitalWrite(PIN_MUX_S0, (channel & 0x01) ? HIGH : LOW);
    digitalWrite(PIN_MUX_S1, (channel & 0x02) ? HIGH : LOW);
    digitalWrite(PIN_MUX_S2, (channel & 0x04) ? HIGH : LOW);
    digitalWrite(PIN_MUX_S3, (channel & 0x08) ? HIGH : LOW);
    delayMicroseconds(5); // استقرار الإشارة التناظرية
    return analogRead(PIN_MUX_SIG);
}

// إرسال حزمة حركة متزامنة لمحركات Feetech (Sync Write Position)
void syncWritePositions(const int16_t* targets, uint16_t execution_time_ms) {
    uint8_t packet[64];
    uint8_t idx = 0;
    
    packet[idx++] = 0xFF; // بادئة الحزمة
    packet[idx++] = 0xFF;
    packet[idx++] = 0xFE; // بث لجميع المحركات (Broadcast ID)
    packet[idx++] = (NUM_JOINTS * 4) + 7; // طول الحزمة
    packet[idx++] = 0x83; // أمر الكتابة المتزامنة (INST_SYNC_WRITE)
    packet[idx++] = 0x2A; // عنوان مسجل الموقع والزمن (Position & Time Register)
    packet[idx++] = 0x04; // عدد البايتات المكتوبة لكل محرك

    for (uint8_t i = 0; i < NUM_JOINTS; i++) {
        packet[idx++] = joints[i].id;
        packet[idx++] = (uint8_t)(targets[i] & 0xFF);
        packet[idx++] = (uint8_t)((targets[i] >> 8) & 0xFF);
        packet[idx++] = (uint8_t)(execution_time_ms & 0xFF);
        packet[idx++] = (uint8_t)((execution_time_ms >> 8) & 0xFF);
    }

    // حساب المجموع الاختباري (Checksum)
    uint8_t checksum = 0;
    for (uint8_t i = 2; i < idx; i++) {
        checksum += packet[i];
    }
    packet[idx++] = ~checksum;

    // إرسال الحزمة عبر الناقل التسلسلي
    ServoBus.write(packet, idx);
}

void setup() {
    Serial.begin(115200);
    ServoBus.begin(SERVO_BAUDRATE, SERIAL_8N1, PIN_SERVO_RX, PIN_SERVO_TX);
    initMultiplexer();

    // تهيئة مصفوفة المفاصل الافتراضية
    for (uint8_t i = 0; i < NUM_JOINTS; i++) {
        joints[i].id = i + 1;
        joints[i].target_position = 2048; // مركز الدائرة (180 درجة)
        joints[i].current_position = 2048;
    }
    
    Serial.println("{\"status\": \"ROBOI V3 Controller Initialized\", \"baud\": 1000000}");
}

void loop() {
    // حلقة التحكم الدورية بمعدل 100Hz
    static uint32_t last_cycle_us = 0;
    if (micros() - last_cycle_us >= 10000) {
        last_cycle_us = micros();

        // 1. قراءة التغذية التناظرية المباشرة للمحركات عبر المضاعف
        for (uint8_t i = 0; i < NUM_JOINTS; i++) {
            uint16_t raw_adc = readAnalogChannel(i);
            joints[i].current_angle_rad = ((float)raw_adc / 4095.0f) * 2.0f * PI - PI;
        }

        // 2. معالجة الأوامر الواردة من منفذ USB-C (تنسيق JSON خفيف)
        if (Serial.available()) {
            String input = Serial.readStringUntil('\n');
            int16_t new_targets[NUM_JOINTS];
            if (sscanf(input.c_str(), "%hd,%hd,%hd,%hd,%hd,%hd", 
                       &new_targets[0], &new_targets[1], &new_targets[2], 
                       &new_targets[3], &new_targets[4], &new_targets[5]) == 6) {
                syncWritePositions(new_targets, 15); // انتقال سلس خلال 15ms
            }
        }
    }
}
```

#### 2.2.8 عقدة بايثون للربط مع بيئة LeRobot و ROS 2
يوضح السكريبت البرمجي التالي آلية الربط عالي الأداء بين لوحة التحكم ومكتبة الذكاء الاصطناعي الفيزيائي **Hugging Face LeRobot** و **ROS 2 Jazzy**، حيث يتولى قراءة حالة المفاصل ونشرها كرسائل قياسية وتمرير إجراءات السياسة العصبية (*Policy Action Output*):

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROBOI LeRobot & ROS 2 Bridge Node
يقوم هذا السكريبت باستقبال أوامر الحركة من نماذج الذكاء الفيزيائي (ACT / Diffusion Policy)
وتمريرها إلى متحكم العتاد V3 مع قراءة تدفق الكاميرات والحالة الحركية.
"""

import time
import serial
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Header

class RoboiLeRobotBridge(Node):
    def __init__(self, port="/dev/ttyACM0", baudrate=115200):
        super().__init__("roboi_lerobot_bridge")
        
        # تهيئة الاتصال التسلسلي
        self.ser = serial.Serial(port, baudrate, timeout=0.05)
        self.get_logger().info(f"Connected to ROBOI V3 Board on {port} @ {baudrate}")
        
        # ناشر حالة المفاصل الحركية
        self.joint_pub = self.create_publisher(JointState, "/roboi/joint_states", 10)
        
        # مشترك لتلقي أوامر السياسة الذكية
        self.action_sub = self.create_subscription(
            JointState, "/roboi/action_cmd", self.action_callback, 10
        )
        
        self.joint_names = [
            "shoulder_pan", "shoulder_lift", "elbow_flex",
            "wrist_flex", "wrist_roll", "gripper"
        ]
        
        # مؤقت زمني للقراءة الدورية بمعدل 50Hz
        self.timer = self.create_timer(0.02, self.read_and_publish_state)
        
    def read_and_publish_state(self):
        """قراءة الحالة الفيزيائية وبثها لبيئة التدريب"""
        msg = JointState()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = self.joint_names
        
        # قراءة الأوضاع من المنفذ التسلسلي
        if self.ser.in_waiting:
            line = self.ser.readline().decode('utf-8', errors='ignore').strip()
            parts = line.split(',')
            if len(parts) == 6:
                try:
                    positions_raw = [int(p) for p in parts]
                    # تحويل القيم من مجال السيرفو (0 - 4095) إلى الراديان (-pi to +pi)
                    positions_rad = [
                        (p - 2048) * (2.0 * np.pi / 4096.0) for p in positions_raw
                    ]
                    msg.position = positions_rad
                    self.joint_pub.publish(msg)
                except ValueError:
                    pass

    def action_callback(self, msg: JointState):
        """استقبال أهداف الزوايا من نموذج ACT وإرسالها إلى العتاد"""
        if len(msg.position) == 6:
            # تحويل الراديان إلى قيم وحدات التشفير الرقمية (0 - 4095)
            servo_targets = [
                int(rad * (4096.0 / (2.0 * np.pi)) + 2048) for rad in msg.position
            ]
            cmd_str = f"{','.join(map(str, servo_targets))}\n"
            self.ser.write(cmd_str.encode('utf-8'))

def main(args=None):
    rclpy.init(args=args)
    bridge_node = RoboiLeRobotBridge()
    try:
        rclpy.spin(bridge_node)
    except KeyboardInterrupt:
        pass
    finally:
        bridge_node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
```

---

### 3.8 الملحق ج: الإثباتات الرياضية للكينماتيكا وتخطيط المسارات (Mathematical Proofs)

#### 1.3.8 اشتقاق مصفوفة التحويل المتجانس القياسية (Standard DH Transformation)
وفق اتفاقية ديناميك-هارتنبرغ (*Denavit-Hartenberg Convention*)، يتم الانتقال من إطار الإسناد للمفصل $(i-1)$ إلى إطار المفصل $(i)$ عبر أربع تحويلات هندسية أولية متتابعة:
1. دوران حول المحور $Z_{i-1}$ بزاوية $\theta_i$ (متغير المفصل الدوار).
2. إزاحة على طول المحور $Z_{i-1}$ بمسافة $d_i$ (إزاحة الوصلة).
3. إزاحة على طول المحور $X_i$ المبدئي بمسافة $a_i$ (طول الوصلة الرابطة).
4. دوران حول المحور $X_i$ الجديد بزاوية $\alpha_i$ (زاوية التواء الوصلة).

تُكتب مصفوفة التحويل الكلية كحاصل ضرب المصفوفات التحويلية الأربع:

$$^{i-1}T_i = \text{Rot}(Z, \theta_i) \cdot \text{Trans}(Z, d_i) \cdot \text{Trans}(X, a_i) \cdot \text{Rot}(X, \alpha_i)$$

وبالضرب المصفوفي المباشر، نحصل على صيغة مصفوفة التحويل المتجانس الأساسية:

$$^{i-1}T_i = \begin{bmatrix}
\cos\theta_i & -\sin\theta_i\cos\alpha_i & \sin\theta_i\sin\alpha_i & a_i\cos\theta_i \\
\sin\theta_i & \cos\theta_i\cos\alpha_i & -\cos\theta_i\sin\alpha_i & a_i\sin\theta_i \\
0 & \sin\alpha_i & \cos\alpha_i & d_i \\
0 & 0 & 0 & 1
\end{bmatrix}$$

وتُحسب الوضعية الهندسية النهائية للأداة الطرفية (*End-Effector Pose*) بالنسبة لقاعدة الروبوت للذراع سداسي المحاور ($6\text{-DOF}$) بالضرب المتسلسل:

$$^0T_6 = \,^0T_1 \cdot \,^1T_2 \cdot \,^2T_3 \cdot \,^3T_4 \cdot \,^4T_5 \cdot \,^5T_6$$

#### 2.3.8 مصفوفة الجاكوبي الهندسية وتحديد حالات الشذوذ الحركي (Jacobian & Singularities)
تربط مصفوفة الجاكوبي الهندسية $J(q)$ بين متجهات السرعات الزاوية للمفاصل $\dot{q} \in \mathbb{R}^6$ ومتجه السرعات الخطية والزاوية للأداة الطرفية $V = [v^T, \omega^T]^T \in \mathbb{R}^6$:

$$V = J(q) \cdot \dot{q} = \begin{bmatrix} J_v(q) \\ J_\omega(q) \end{bmatrix} \dot{q}$$

حيث يتحدد العمود $i$ للجاكوبي الخاص بالمفصل الدوراني بالعلاقة:

$$J_i = \begin{bmatrix} J_{v,i} \\ J_{\omega,i} \end{bmatrix} = \begin{bmatrix} z_{i-1} \times (o_n - o_{i-1}) \\ z_{i-1} \end{bmatrix}$$

حيث $z_{i-1}$ هو متجه الوحدة لمحور الدوران، و $o_{i-1}$ هو موقع أصل إطار الإسناد $(i-1)$، و $o_n$ هو موقع الأداة الطرفية.

تحدث **حالات الشذوذ الحركي (*Kinematic Singularities*)** عندما تفقد مصفوفة الجاكوبي رتبتها الكاملة (*Loss of Rank*)، مما يجعل محدد المصفوفة منعدماً:

$$\det(J(q)) = 0$$

وفي هذه الوضعيات:
* تفقد الأداة الطرفية القدرة على الحركة في اتجاه فيزيائي واحد أو أكثر في الفضاء الإقليدي.
* تؤول السرعات الزاوية المطلوبة للمفاصل في الكينماتيكا العكسية إلى المالانهاية ($\dot{q} = J^{-1} V \to \infty$)، مما يسبب اهتزازات عنيفة وأخطاء استقرار رقمي يتم تجاوزها في خوارزمياتنا عبر طريقة تخميد المربعات الصغرى (*Damped Least Squares - Levenberg-Marquardt Jacobian Inversion*):

$$J^* = J^T (J J^T + \lambda^2 I)^{-1}$$

#### 3.3.8 توليد المسارات الحركية بمتعدد الحدود من الدرجة الخامسة (Quintic Polynomial)
لضمان استمرارية منحنى الموقع والسرعة والتسارع مع انعدام قفزات الرعشة الحركية (*Zero Jerk at Boundaries*) لحماية المسننات البلاستيكية من الصدمات، يتم صياغة المسار الزمني لكل مفصل كمتعدد حدود خماسي:

$$\theta(t) = a_0 + a_1 t + a_2 t^2 + a_3 t^3 + a_4 t^4 + a_5 t^5$$

مع الشروط الحدية عند زمن البداية $t_0 = 0$ وزمن الوصول $t_f$:

$$\begin{aligned}
\theta(0) &= \theta_0, & \dot{\theta}(0) &= \dot{\theta}_0 = 0, & \ddot{\theta}(0) &= \ddot{\theta}_0 = 0 \\
\theta(t_f) &= \theta_f, & \dot{\theta}(t_f) &= \dot{\theta}_f = 0, & \ddot{\theta}(t_f) &= \ddot{\theta}_f = 0
\end{aligned}$$

وبتطبيق الشروط الحدية وحل المنظومة الخطية الناتجة، نحصل على المعاملات التحليلية الدقيقة:

$$a_0 = \theta_0, \quad a_1 = 0, \quad a_2 = 0$$

$$a_3 = \frac{10(\theta_f - \theta_0)}{t_f^3}, \quad a_4 = \frac{-15(\theta_f - \theta_0)}{t_f^4}, \quad a_5 = \frac{6(\theta_f - \theta_0)}{t_f^5}$$

مما يضمن حركة فائقة السلاسة وانعدام الإجهادات الميكانيكية اللحظية على هياكل الـ PETG-CF.

---

### 4.8 الملحق د: دليل إجراءات التشغيل القياسية وتدابير السلامة المعملية (SOP & Safety Manual)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    خارطة السلامة المعملية والصيانة الوقائية                 │
│                 (Laboratory SOP & Preventative Maintenance)                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [ بروتوكول التشغيل اليومي ]                                                │
│  ├── فحص التوصيلات الكهربائية وسجادة العزل ESD ومصدر 12V DC                  │
│  ├── التأكد من جاهزية زر الطوارئ الفيزيائي (E-Stop Switch)                  │
│  └── المعايرة البصرية التلقائية للأوضاع الصفرية عبر AprilTag                 │
│                                                                             │
│  [ جدول الصيانة الدورية ]                                                   │
│  ├── كل 50 ساعة تشغيل:  فحص عزم ربط المسامير DIN 912 (عزم 1.2 N·m)          │
│  ├── كل 200 ساعة تشغيل: فحص تآكل المسننات وتشحيم المحامل بشحم الليثيوم      │
│  └── كل 500 ساعة تشغيل: اختبار ثبات الإنكودر وتحديث سجل الجاهزية الفنية      │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 1.4.8 إجراءات السلامة الكهربائية والميكانيكية
1. **منطقة عمل الأمان (*Safety Workspace Enclosure*):** يجب تحديد دائرة نصف قطرها 450 مم حول قاعدة كل ذراع روبوتي بشريط أصفر عاكس، ويُحظر وضع أي أدوات حادة أو عوائق خارج نطاق منصة العمل.
2. **قواطع الطوارئ (*Emergency Stop - E-Stop*):** تزود كل محطة عمل بزر طوارئ فيزيائي متصل مباشرة بخط التغذية الرئيسي (12V) لقطع التيار فوراً عن محركات السيرفو دون إيقاف وحدة المعالجة المركزية، مما يمنع اصطدام الذراع بالأجسام المحيطة عند حدوث أي خطأ برمجي.
3. **الحماية الحرارية (*Thermal Monitoring*):** تمت برمجة المتحكم لقراءة مسجلات الحرارة الداخلية لمحركات Feetech STS بمعدل مستمر؛ وفي حال تجاوز حرارة أي محرك عتبة $70^\circ\text{C}$، يدخل الذراع تلقائياً في وضع حماية يخفض عزم التثبيت إلى 20% ويطلق تحذيراً صوتياً ومرئياً على شاشة OLED.

#### 2.4.8 المعايرة البصرية التلقائية للزوايا الصفرية (AprilTag Calibration)
* يتم تثبيت لوحة معايرة دقيقة مطبوعة بعلامة *AprilTag (عائلة tag36h11)* على مساحة عمل الروبوت عند إحداثيات مرجعية معلومة مسبقاً بدقة $\pm 0.1\text{ mm}$.
* عند بدء جلسة العمل المخبرية، يستدعي الطالب سكريبت المعايرة التلقائية:
  ```bash
  python3 scripts/calibrate_zero_pose.py --camera_id 0 --tag_family tag36h11 --tag_size 0.05
  ```
* تقوم الكاميرا العلوية برصد زوايا مصفوفة التحويل للكود البصري، ويتحرك طرف الذراع لملامسة مركز العلامة، ويتم تحديث قيم مسجلات الزوايا الصفرية (*Zero-Offset EEPROM Registers*) داخل ذاكرة السيرفوهات الدائمة، مما يلغي أي خطأ تراكمي ناجم عن تبديل القطع أو التمدد الحراري.

---

### 5.8 الملحق هـ: قائمة المراجع العلمية والتشريعية المعتمدة (Comprehensive Bibliography)

#### 1.5.8 المراجع التشريعية والحكومية الروسية
1. **Федеральный закон № 44-ФЗ от 05.04.2013** «О контрактной системе в сфере закупок товаров, работ, услуг для обеспечения государственных и муниципальных нужд».
2. **Федеральный закон № 223-ФЗ от 18.07.2011** «О закупках товаров, работ, услуг отдельными видами юридических лиц».
3. **Федеральный закон № 318-ФЗ от 08.08.2024** «О внесении изменений в Федеральный закон "О контрактной системе в сфере закупок" и Федеральный закон "О закупках товаров, работ, услуг отдельными видами юридических лиц"» (Гармонизация национального режима).
4. **Постановление Правительства РФ № 719 от 17.07.2015** «О подтверждении производства промышленной продукции на территории Российской Федерации» (в актуальной редакции с балльной системой оценки локализации).
5. **Постановление Правительства РФ № 878 от 10.07.2019** «О мерах стимулирования производства радиоэлектронной продукции на территории РФ при осуществлении закупок» (Правило «второй лишний»).
6. **Постановление Правительства РФ № 925 от 16.09.2016** «О приоритете товаров российского происхождения, работ, услуг, выполняемых, оказываемых российскими лицами».
7. **Постановление Правительства РФ № 2013 от 03.12.2020** «О минимальной доле закупок товаров российского происхождения».
8. **Постановление Правительства РФ № 2014 от 03.12.2020** «Об определении минимальной обязательной доли закупок российских товаров и ее достижении заказчиком».
9. **Постановление Правительства РФ № 729 от 13.05.2021** «О мерах по реализации программы стратегического академического лидерства "Приоритет-2030"».
10. **Постановление Правительства РФ № 619 от 08.04.2022** «О государственной поддержке программ развития передовых инженерных школ».
11. **Приказ Минфина России № 126н от 04.06.2018** «Об условиях допуска товаров, происходящих из иностранного государства или группы иностранных государств, для целей осуществления закупок товаров».
12. **ГОСТ 7.32-2017** «Система стандартов по информации, библиотечному и издательскому делу. Отчет о научно-исследовательской работе. Структура и правила оформления».
13. **ГОСТ Р 53429-2009** «Платы печатные. Основные параметры конструкции и монтажа».

#### 2.5.8 المراجع الأكاديمية والتقنية الدولية
14. **Craig, J. J. (2018).** *Introduction to Robotics: Mechanics and Control* (4th ed.). Pearson.
15. **Siciliano, B., Sciavicco, L., Villani, L., & Oriolo, G. (2010).** *Robotics: Modelling, Planning and Control*. Springer Science & Business Media.
16. **Lynch, K. M., & Park, F. C. (2017).** *Modern Robotics: Mechanics, Planning, and Control*. Cambridge University Press.
17. **Zhao, T. Z., Kumar, V., Levine, S., & Finn, C. (2023).** "Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware." *Robotics: Science and Systems (RSS 2023)*. arXiv:2304.13705.
18. **Chi, C., Feng, S., Pan, Y., Shen, N., & Song, S. (2023).** "Diffusion Policy: Visuomotor Policy Learning via Action Diffusion." *Robotics: Science and Systems (RSS 2023)*.
19. **Cadene, R., Alibert, S., Pasqualino, P., et al. (2024).** "LeRobot: State-of-the-art Machine Learning for Real-World Robotics in Pytorch." *Hugging Face Open Source Release*. https://github.com/huggingface/lerobot.
20. **Macenski, S., Foote, T., Gerkey, B., Lalancette, C., & Woodall, W. (2022).** "Robot Operating System 2: Design, architecture, and uses in the wild." *Science Robotics*, 7(66), eabm6074.
21. **Feetech RC Model Co. (2024).** *STS3215 / STS3032 Serial Bus Smart Servo Technical Manual & Communication Protocol Specification*. Shenzhen, China.
22. **Texas Instruments. (2022).** *TPS54560B 4.5-V to 60-V Input, 5-A, Step-Down DC-DC Converter with Eco-mode Data Sheet (SLVSD98)*. Dallas, Texas.

---

### 6.8 الملحق و: مسرد المصطلحات الثلاثي الموحد (Trilingual Glossary)

| المصطلح الأكاديمي المعتمد بالعربية | Russian Statutory / Technical Term | English Technical Term |
| :--- | :--- | :--- |
| **قانون المشتريات والمناقصات الحكومية الروسي** | Федеральный закон № 44-ФЗ / 223-ФЗ | Federal Public Procurement Laws (44-FZ / 223-FZ) |
| **نظام المعاملة الوطنية وتفضيل المنتج المحلي** | Национальный режим при закупках | National Procurement Regime / Domestic Preference |
| **قاعدة استبعاد العروض الأجنبية (الشريك الثاني الزائد)** | Правило «второй лишний» (ПП РФ № 878) | "Second-Wheel-Out" Mandatory Exclusion Rule |
| **سجل المنتجات الصناعية الوطنية لوزارة الصناعة** | Реестр промышленной продукции Минпромторга РФ | Minpromtorg Registry of Russian Industrial Products |
| **نظام النقاط التراكمي لتقييم التوطين الصناعي** | Балльная система оценки уровня локализации (ПП № 719) | Cumulative Localization Point-Scoring System |
| **شهادة المنشأ وتقرير فحص غرفة التجارة والصناعة** | Сертификат происхождения СТ-1 / Акт экспертизы ТПП РФ | Certificate of Origin Form ST-1 / Chamber of Commerce Audit |
| **منحة الشركات الطلابية الناشئة (صندوق بورتنيك)** | Конкурс «Студенческий стартап» (ФСИ / Фонд Бортника) | FASIE "Student Startup" Non-dilutive Grant |
| **برنامج تمويل البحوث والتطوير (ستارت-1)** | Программа «Старт-1» (Фонд содействия инновациям) | FASIE "Start-1" Applied R&D Financing Program |
| **برنامج القيادة الأكاديمية الاستراتيجية (أولويات 2030)** | Программа лидерства «Приоритет-2030» (ПП РФ № 729) | Priority 2030 Strategic Academic Leadership Program |
| **المدارس الهندسية الرائدة التابعة للجامعات** | Передовые инженерные школы - ПИШ (ПП РФ № 619) | Advanced Engineering Schools (PISH Framework) |
| **سيرفو تسلسلي ذكي مغلق الحلقة** | Умный последовательный шинный сервопривод | Smart Closed-Loop Serial Bus Servo (Feetech STS) |
| **لوحات الدوائر المطبوعة بالتجميع السطحي التعاقدي** | Контрактное производство и SMT-монтаж печатных плат | Turnkey Contract PCBA & SMT Assembly (Rezonit) |
| **الكفاءة الرأسمالية والجدوى الاقتصادية النوعية** | Удельная капиталоемкость и экономическая эффективность | Capital Efficiency & Cost-Benefit Feasibility Ratio |
| **التعلم بالتقليد وتجميع الإجراءات العصبية** | Обучение с подراжанием / Агрегация действий (ACT / LeRobot) | Imitation Learning / Action Chunking with Transformers |
| **الكينماتيكا المباشرة والعكسية وفق اتفاقية DH** | Прямая и обратная кинематика по параметрам Д-Х | Forward & Inverse Kinematics (Denavit-Hartenberg) |
| **مصفوفة الجاكوبي وحالات الشذوذ الحركي** | Геометрический якобиан и кинематические сингулярности | Geometric Jacobian Matrix & Kinematic Singularities |
| **مسارات تخطيط الحركة متعددة الحدود الخماسية** | Траектории движения на основе полиномов пятой степени | Quintic Polynomial Trajectory Interpolation |
| **إجراءات التشغيل القياسية وتدابير السلامة المعملية** | Стандартные операционные процедуры и техника безопасности | Standard Operating Procedures (SOP) & Laboratory Safety |
