#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// --- إعدادات الشاشة OLED ---
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// --- إعدادات متحكم السيرفو PCA9685 ---
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();
#define USMIN  500    // طول النبضة عند زاوية 0 (بالميكروثانية)
#define USMAX  2500   // طول النبضة عند زاوية 180 (بالميكروثانية)
#define SERVO_FREQ 50 // التردد 50Hz

// --- دبابيس الـ Rotary Encoder (HW-040) على Arduino Pro Mini ---
const int encCLK = 2; // Pin D2 (يدعم Hardware Interrupt INT0)
const int encDT  = 3; // Pin D3 (يدعم Hardware Interrupt INT1)
const int encSW  = 4; // Pin D4 (زر الضغط)

// متغيرات القنوات والزوايا
// القناة 0 ملغية / غير مستخدمة بناءً على طلبك
volatile int currentSelectedChannel = 1; // نبدأ من القناة 1
int currentAngles[16];
int currentMicro[16];
int targetMicro[16];

// متغيرات الانتربت
volatile bool encoderMoved = false;
volatile int encoderDir = 0;
volatile bool buttonPressed = false;

// إعدادات الحركة الناعمة (Smooth Motion)
unsigned long lastUpdateMillis = 0;
const int SMOOTH_DELAY = 15; // ملي ثانية بين كل حركة تدريجية
const int SMOOTH_STEP = 25;  // حجم الخطوة بالميكروثانية

// ISR لدوران الـ Rotary Encoder
void encoderISR() {
  static unsigned long lastInterruptTime = 0;
  unsigned long interruptTime = millis();
  if (interruptTime - lastInterruptTime > 5) { // مانع ارتداد 5ms
    if (digitalRead(encDT) != digitalRead(encCLK)) {
      encoderDir = 1;  // يمين (زيادة)
    } else {
      encoderDir = -1; // شمال (نقصان)
    }
    encoderMoved = true;
    lastInterruptTime = interruptTime;
  }
}

// تحديث بيانات الشاشة OLED
void updateDisplay(int channel, int angle) {
  display.clearDisplay();
  
  // الجزء العلوي (أول 16 بكسل - لون أصفر بالشاشات ثنائية اللون)
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(18, 4);
  display.println(F("SERVO TESTER READY"));
  
  // خط فاصل أنيق
  display.drawLine(0, 15, 128, 15, SSD1306_WHITE);
  
  // الجزء السفلي (اللون الأزرق)
  display.setTextSize(2);
  display.setCursor(10, 24);
  display.print(F("CH : "));
  display.println(channel);
  
  display.setCursor(10, 46);
  display.print(F("ANG: "));
  display.print(angle);
  display.setTextSize(1);
  display.print((char)247); // علامة الدرجة °
  
  display.display();
}

void setup() {
  Serial.begin(9600);
  Serial.println(F("Pro Mini + PCA9685 + HW-040 Encoder Ready."));

  // تهيئة دبابيس الـ Encoder مع Pull-up الداخلي
  pinMode(encCLK, INPUT_PULLUP);
  pinMode(encDT, INPUT_PULLUP);
  pinMode(encSW, INPUT_PULLUP);

  // تفعيل المقاطعة (Interrupts) على Pin D2
  attachInterrupt(digitalPinToInterrupt(encCLK), encoderISR, FALLING);

  // تهيئة مشغل السيرفو PCA9685 عبر I2C (A4: SDA, A5: SCL)
  pwm.begin();
  pwm.setOscillatorFrequency(27000000);
  pwm.setPWMFreq(SERVO_FREQ);

  // تهيئة زوايا ونبضات كل القنوات على 90 درجة افتراضياً
  for (int i = 0; i < 16; i++) {
    currentAngles[i] = 90;
    currentMicro[i] = map(90, 0, 180, USMIN, USMAX);
    targetMicro[i] = currentMicro[i];
    if (i != 0) { // تجاهل القناة 0
      pwm.writeMicroseconds(i, currentMicro[i]);
    }
  }

  // تهيئة شاشة OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("OLED init failed!"));
  } else {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(16, 4);
    display.println(F("SYSTEM STARTED"));
    display.drawLine(0, 15, 128, 15, SSD1306_WHITE);
    
    display.setTextSize(2);
    display.setCursor(15, 30);
    display.println(F("TESTER READY"));
    display.display();
  }

  delay(500);
  // عرض القناة الافتراضية الأولى (CH: 1)
  updateDisplay(currentSelectedChannel, currentAngles[currentSelectedChannel]);
  Serial.print(F("SEL:"));
  Serial.println(currentSelectedChannel);
}

void loop() {
  // 1. فحص زر الـ Rotary Encoder لتغيير القناة (SW)
  static int lastButtonState = HIGH;
  static unsigned long lastDebounceTime = 0;
  int buttonReading = digitalRead(encSW);

  if (buttonReading != lastButtonState) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > 50) {
    if (buttonReading == LOW && !buttonPressed) {
      buttonPressed = true;
      
      // الانتقال للقناة التالية وتخطي القناة 0
      currentSelectedChannel++;
      if (currentSelectedChannel > 15) {
        currentSelectedChannel = 1; // الدوران من 1 إلى 15 (استبعاد 0)
      }

      // تحديث الشاشة والسيريال
      updateDisplay(currentSelectedChannel, currentAngles[currentSelectedChannel]);
      Serial.print(F("SEL:"));
      Serial.println(currentSelectedChannel);
    } else if (buttonReading == HIGH) {
      buttonPressed = false;
    }
  }
  lastButtonState = buttonReading;

  // 2. فحص دوران الـ Rotary Encoder لتعديل الزاوية
  if (encoderMoved) {
    encoderMoved = false;
    int step = 2; // سرعة تعديل الزاوية بكل تكة (درجتان)
    int newAngle = currentAngles[currentSelectedChannel] + (encoderDir * step);

    if (newAngle < 0) newAngle = 0;
    if (newAngle > 180) newAngle = 180;

    if (newAngle != currentAngles[currentSelectedChannel]) {
      currentAngles[currentSelectedChannel] = newAngle;
      targetMicro[currentSelectedChannel] = map(newAngle, 0, 180, USMIN, USMAX);

      // تحديث الشاشة
      updateDisplay(currentSelectedChannel, newAngle);

      // إشعار السيريال لتحديث الواجهة (GUI)
      Serial.print(F("UPD:"));
      Serial.print(currentSelectedChannel);
      Serial.print(F(":"));
      Serial.println(newAngle);
    }
  }

  // 3. قراءة أوامر السيريال القادمة من الكمبيوتر (Python GUI)
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    int sepIndex = command.indexOf(':');
    if (sepIndex == -1) {
      sepIndex = command.indexOf(','); // دعم الفاصلتين , أو :
    }

    if (sepIndex > 0) {
      int ch = command.substring(0, sepIndex).toInt();
      int ang = command.substring(sepIndex + 1).toInt();

      // التحقق من القناة (استبعاد القناة 0 بناءً على طلبك)
      if (ch >= 1 && ch <= 15 && ang >= 0 && ang <= 180) {
        currentAngles[ch] = ang;
        targetMicro[ch] = map(ang, 0, 180, USMIN, USMAX);
        currentSelectedChannel = ch;

        updateDisplay(ch, ang);

        Serial.print(F("UPD:"));
        Serial.print(ch);
        Serial.print(F(":"));
        Serial.println(ang);
      }
    }
  }

  // 4. تحريك السيرفوهات بنعومة فائقة (Smooth Motion) نحو الزوايا المحددة
  unsigned long currentMillis = millis();
  if (currentMillis - lastUpdateMillis >= SMOOTH_DELAY) {
    lastUpdateMillis = currentMillis;
    for (int i = 1; i <= 15; i++) { // تخطي القناة 0
      if (currentMicro[i] != targetMicro[i]) {
        if (currentMicro[i] < targetMicro[i]) {
          currentMicro[i] += SMOOTH_STEP;
          if (currentMicro[i] > targetMicro[i]) currentMicro[i] = targetMicro[i];
        } else {
          currentMicro[i] -= SMOOTH_STEP;
          if (currentMicro[i] < targetMicro[i]) currentMicro[i] = targetMicro[i];
        }
        pwm.writeMicroseconds(i, currentMicro[i]);
      }
    }
  }
}