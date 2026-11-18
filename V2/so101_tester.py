"""
====================================================================
SO-100 / SO-101 (SO-ARM100) Feetech STS3215 Diagnostic & Test Suite
====================================================================
هذا البرنامج مخصص لاختبار ذراع SO-100 / SO-101 المزود بمحركات Feetech STS3215
متصل عبر بوردة Waveshare Bus Servo Adapter (CH343 / Type-C) على منفذ COM38.
"""

import sys
import time
import serial
import serial.tools.list_ports

# أسماء مفاصل الذراع الافتراضية في معمارية LeRobot SO-100
JOINT_NAMES = {
    1: "Joint 1 - Shoulder Pan (القاعدة / الدوران الأفقي)",
    2: "Joint 2 - Shoulder Lift (مفصل الكتف / الرفع)",
    3: "Joint 3 - Elbow Flex (مفصل الكوع)",
    4: "Joint 4 - Wrist Flex (مفصل الرسغ - الإمالة)",
    5: "Joint 5 - Wrist Roll (مفصل الرسغ - الدوران المحوري)",
    6: "Joint 6 - Gripper (القابض / الملقط)"
}

class SO101Controller:
    # أوامر بروتوكول Feetech STS
    INST_PING = 0x01
    INST_READ = 0x02
    INST_WRITE = 0x03
    INST_REG_WRITE = 0x04
    INST_ACTION = 0x05
    INST_RESET = 0x06

    # عناوين السجلات (Memory Map - STS3215)
    REG_ID = 0x05             # 1 byte
    REG_BAUD = 0x06           # 1 byte (0=1M, 1=0.5M, 2=250k, 3=128k, 4=115.2k)
    REG_RETURN_DELAY = 0x07   # 1 byte
    REG_TORQUE_ENABLE = 0x28  # 1 byte (0=Free, 1=Torque On)
    REG_GOAL_POSITION = 0x2A  # 2 bytes (0 - 4095)
    REG_GOAL_TIME = 0x2C      # 2 bytes
    REG_GOAL_SPEED = 0x2E     # 2 bytes
    REG_LOCK = 0x37           # 1 byte (0=EEPROM Unlock, 1=Lock)
    REG_PRESENT_POS = 0x38    # 2 bytes
    REG_PRESENT_SPEED = 0x3A  # 2 bytes
    REG_PRESENT_LOAD = 0x3C   # 2 bytes
    REG_PRESENT_VOLT = 0x3E   # 1 byte (0.1V)
    REG_PRESENT_TEMP = 0x3F   # 1 byte (°C)

    def __init__(self, port="COM38", baudrate=1000000, timeout=0.04):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            return True
        except Exception as e:
            print(f"[!] فشل فتح المنفذ {self.port}: {e}")
            return False

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    @staticmethod
    def calc_checksum(packet_body):
        return (~sum(packet_body)) & 0xFF

    def write_reg(self, servo_id, addr, values):
        """كتابة قيم إلى سجلات المحرك (بدون انتظار رد)"""
        length = len(values) + 3
        body = [servo_id, length, self.INST_WRITE, addr] + values
        chk = self.calc_checksum(body)
        pkt = bytes([0xFF, 0xFF] + body + [chk])
        self.ser.reset_input_buffer()
        self.ser.write(pkt)
        time.sleep(0.003)

    def read_reg(self, servo_id, addr, length, retries=3):
        """قراءة بايتات من سجلات المحرك مع معالجة ذكية لفقدان البايتات في Half-Duplex"""
        for _ in range(retries):
            self.ser.reset_input_buffer()
            body = [servo_id, 0x04, self.INST_READ, addr, length]
            chk = self.calc_checksum(body)
            pkt = bytes([0xFF, 0xFF] + body + [chk])
            self.ser.write(pkt)
            
            t0 = time.time()
            buf = bytearray()
            while time.time() - t0 < self.timeout:
                if self.ser.in_waiting:
                    buf += self.ser.read(self.ser.in_waiting)
                    # البحث عن باقة الرد
                    for i in range(len(buf)):
                        if buf[i] == servo_id and i + 1 < len(buf):
                            pkt_len = buf[i+1]
                            total_bytes = pkt_len + 2
                            if i + total_bytes <= len(buf):
                                candidate = buf[i : i + total_bytes]
                                if self.calc_checksum(candidate[:-1]) == candidate[-1]:
                                    # candidate[2] is error, data is candidate[3:-1]
                                    return bytes(candidate[3:-1])
                time.sleep(0.001)
        return None

    def ping(self, servo_id, retries=2):
        for _ in range(retries):
            self.ser.reset_input_buffer()
            body = [servo_id, 0x02, self.INST_PING]
            chk = self.calc_checksum(body)
            self.ser.write(bytes([0xFF, 0xFF] + body + [chk]))
            
            t0 = time.time()
            buf = bytearray()
            while time.time() - t0 < 0.03:
                if self.ser.in_waiting:
                    buf += self.ser.read(self.ser.in_waiting)
                    for i in range(len(buf)):
                        if buf[i] == servo_id and i + 1 < len(buf):
                            pkt_len = buf[i+1]
                            total = pkt_len + 2
                            if i + total <= len(buf):
                                cand = buf[i : i + total]
                                if self.calc_checksum(cand[:-1]) == cand[-1]:
                                    return True
                time.sleep(0.001)
        return False

    def get_joint_state(self, servo_id):
        """قراءة زاوية المفصل، الجهد، ودرجة الحرارة"""
        data = self.read_reg(servo_id, self.REG_PRESENT_POS, 8)
        if data and len(data) == 8:
            pos = int.from_bytes(data[0:2], byteorder='little')
            speed = int.from_bytes(data[2:4], byteorder='little', signed=True)
            load = int.from_bytes(data[4:6], byteorder='little', signed=True)
            volt = data[6] / 10.0
            temp = data[7]
            angle = pos * 360.0 / 4096.0
            return {
                "id": servo_id,
                "pos_raw": pos,
                "angle_deg": round(angle, 1),
                "voltage": volt,
                "temperature": temp,
                "speed": speed,
                "load": load
            }
        return None

    def set_torque(self, servo_id, enable=True):
        """تفعيل أو إلغاء عزم التثبيت (Torque) للمحرك"""
        val = 1 if enable else 0
        self.write_reg(servo_id, self.REG_TORQUE_ENABLE, [val])

    def set_all_torque(self, ids, enable=True):
        for sid in ids:
            self.set_torque(sid, enable)

    def move_joint(self, servo_id, goal_pos, speed=500, acc=50):
        """تحريك المحرك إلى موضع محدد (0 - 4095) بسرعة وتسارع محددين"""
        pos_b = list(int(goal_pos).to_bytes(2, 'little'))
        time_b = [0, 0]
        spd_b = list(int(speed).to_bytes(2, 'little'))
        self.write_reg(servo_id, self.REG_GOAL_POSITION, pos_b + time_b + spd_b)

    def change_servo_id(self, current_id, new_id):
        """تغيير معرّف المحرك في ذاكرة EEPROM (يجب توصيل محرك واحد فقط أثناء هذه العملية!)"""
        print(f"[*] فك حماية الذاكرة (Unlock EEPROM) للمحرك {current_id}...")
        self.write_reg(current_id, self.REG_LOCK, [0])
        time.sleep(0.05)
        print(f"[*] تعيين المعرف الجديد: {new_id}...")
        self.write_reg(current_id, self.REG_ID, [new_id])
        time.sleep(0.05)
        print(f"[*] إعادة قفل الذاكرة (Lock EEPROM) للمعرف {new_id}...")
        self.write_reg(new_id, self.REG_LOCK, [1])
        time.sleep(0.05)
        
        # تحقق من الرد
        ok = self.ping(new_id)
        return ok


def auto_detect_port():
    """البحث التلقائي عن منفذ بوردة السيرفو"""
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        desc = (p.description or "").lower()
        hwid = (p.hwid or "").lower()
        if "1a86" in hwid or "ch343" in desc or "ch340" in desc or "serial" in desc:
            return p.device
    if ports:
        return ports[0].device
    return "COM38"


def menu_scan(arm):
    print("\n" + "="*50)
    print("           فحص المحركات على الشبكة (Bus Scan)")
    print("="*50)
    print("[*] جارٍ فحص المعرفات من 1 إلى 6 (ومعرفات إضافية حتى 10)...")
    found = []
    for sid in range(1, 11):
        name = JOINT_NAMES.get(sid, f"Joint {sid}")
        state = arm.get_joint_state(sid)
        if state is not None:
            found.append(sid)
            print(f"  [+] تم العثور على {name}:")
            print(f"      - الزاوية الحالية: {state['angle_deg']}° (Raw: {state['pos_raw']})")
            print(f"      - جهد التغذية:     {state['voltage']} V")
            print(f"      - درجة الحرارة:    {state['temperature']} °C")
        else:
            # تجربة ping سريع
            if arm.ping(sid):
                found.append(sid)
                print(f"  [+] تم العثور على {name} (Ping ناجح)")
    
    if not found:
        print("\n[!] لم يستجب أي محرك!")
        print("  تأكد من:")
        print("  1. توصيل محول الطاقة 12V بالبوردة وتشغيل المفتاح (يجب إضاءة LED الباور).")
        print("  2. وضع الـ Jumper على الوضع B (USB).")
        print("  3. سلامة كابل السيرفو ثلاثي الأسلاك.")
    else:
        print(f"\n[✓] إجمالي المحركات المتصلة بنجاح: {len(found)} محرك: {found}")
    return found


def menu_live_monitor(arm, active_ids):
    if not active_ids:
        print("[!] يرجى عمل فحص للمحركات أولاً.")
        return
    
    print("\n" + "="*50)
    print("     المراقبة الحية لزوايا الذراع (Live Monitor)")
    print("="*50)
    print("[*] تم إلغاء عزم المحركات (Free Torque) لتتمكن من تحريك الذراع بيدك بحرية.")
    print("[*] اضغط Ctrl+C للخروج والعودة للقائمة الرئيسية.\n")
    
    arm.set_all_torque(active_ids, enable=False)
    time.sleep(0.1)
    
    try:
        while True:
            line_parts = []
            for sid in active_ids:
                state = arm.get_joint_state(sid)
                if state:
                    line_parts.append(f"J{sid}: {state['angle_deg']:5.1f}° ({state['voltage']:.1f}V)")
                else:
                    line_parts.append(f"J{sid}: ---.-°")
            print("\r" + " | ".join(line_parts), end="", flush=True)
            time.sleep(0.08)
    except KeyboardInterrupt:
        print("\n\n[✓] تم إنهاء المراقبة الحية.")


def menu_wiggle_test(arm, active_ids):
    if not active_ids:
        print("[!] يرجى فحص وتحديد المحركات أولاً.")
        return

    print("\n" + "="*50)
    print("     اختبار الحركة اللطيف (Gentle Wiggle Test)")
    print("="*50)
    print("تحذير: سيقوم البرنامج بتحريك كل مفصل بمقدار صغير جداً (+5 درجات ثم -5 درجات)")
    print("للتأكد من استجابة المحرك والتروس ميكانيكياً.")
    ans = input("هل تريد المتابعة؟ (y/n): ").strip().lower()
    if ans != 'y':
        return

    for sid in active_ids:
        name = JOINT_NAMES.get(sid, f"Joint {sid}")
        print(f"\n[*] اختبار المفصل {name}...")
        state = arm.get_joint_state(sid)
        if not state:
            print("  [!] تعذر قراءة الموضع الأولي، تخطي...")
            continue
        
        orig_pos = state["pos_raw"]
        # +50 خطوة (~4.4 درجة)
        target1 = min(4000, orig_pos + 60)
        target2 = max(100, orig_pos - 60)

        arm.set_torque(sid, True)
        time.sleep(0.05)

        print(f"  -> خطوة 1: تحريك خفيف للأمام (+60 units)...")
        arm.move_joint(sid, target1, speed=300)
        time.sleep(0.6)

        print(f"  -> خطوة 2: تحريك خفيف للخلف (-60 units)...")
        arm.move_joint(sid, target2, speed=300)
        time.sleep(0.6)

        print(f"  -> إعادة المفصل إلى موضعه الأصلي ({orig_pos})...")
        arm.move_joint(sid, orig_pos, speed=300)
        time.sleep(0.6)
        print(f"  [✓] اكتمل اختبار المفصل {sid} بنجاح.")

    print("\n[✓] انتهى اختبار الحركة لجميع المحركات.")


def menu_program_id(arm):
    print("\n" + "="*50)
    print("        أداة برمجة معرفات المحركات (ID Setup)")
    print("="*50)
    print("تنبيه هام جداً:")
    print("1. يجب توصيل **محرك واحد فقط** في كل مرة بالبوردة أثناء تغيير الـ ID!")
    print("2. إذا كانت كل المحركات موصولة معاً وهي جميعاً تحمل ID=1 الافتراضي،")
    print("   فإن تغيير الـ ID سيغيرها جميعاً في نفس اللحظة!")
    print("-" * 50)
    
    current_id_str = input("أدخل المعرّف الحالي للمحرك المتصل (الافتراضي عادة 1): ").strip()
    new_id_str = input("أدخل المعرّف الجديد المطلوب لهذا المحرك (1 إلى 6): ").strip()

    try:
        cur_id = int(current_id_str)
        new_id = int(new_id_str)
    except ValueError:
        print("[!] خطأ: يجب إدخال أرقام صحيحة.")
        return

    if new_id < 1 or new_id > 253:
        print("[!] رقم المعرف غير صالح.")
        return

    print(f"\n[*] جارٍ محاولة تغيير المعرف من {cur_id} إلى {new_id}...")
    success = arm.change_servo_id(cur_id, new_id)
    if success:
        print(f"[✓✓✓] تم بنجاح! المحرك الآن يستجيب للمعرّف الجديد: {new_id}")
        state = arm.get_joint_state(new_id)
        if state:
            print(f"    الزاوية: {state['angle_deg']}° | الجهد: {state['voltage']}V")
    else:
        print(f"[!] لم يتم التأكد من الاستجابة على المعرف {new_id}.")
        print("تأكد أن المحرك المتصل هو الوحيد على البوردة وأن التغذية 12V متصلة.")


def main():
    detected_port = auto_detect_port()
    print("="*60)
    print("   برنامج فحص واختبار ذراع SO-100 / SO-101 (Feetech STS3215)")
    print("="*60)
    print(f"المنفذ المكتشف: {detected_port}")
    
    port_choice = input(f"اضغط Enter لاستخدام [{detected_port}] أو اكتب اسم منفذ آخر: ").strip()
    port = port_choice if port_choice else detected_port

    arm = SO101Controller(port=port, baudrate=1000000)
    if not arm.connect():
        print("[!] فشل الاتصال بالمنفذ التسلسلي. تأكد من إغلاق أي برنامج آخر يستخدم المنفذ.")
        return

    print(f"[✓] تم الاتصال بالمنفذ {port} بنجاح بسرعة 1,000,000 Baud.")
    active_ids = []

    try:
        while True:
            print("\n" + "-"*40)
            print("القائمة الرئيسية:")
            print("1. فحص المحركات المتصلة (Scan Bus)")
            print("2. قراءة زوايا المفاصل المباشرة مع تحريك الذراع باليد (Live Monitor)")
            print("3. اختبار حركة لطيف للمفاصل (Gentle Wiggle Test)")
            print("4. إلغاء عزم جميع المحركات (Torque OFF - تحريك يدوي حر)")
            print("5. تفعيل عزم جميع المحركات (Torque ON - تثبيت الموضع)")
            print("6. برمجة معرف محرك مفرد (Program Single Servo ID)")
            print("0. خروج")
            print("-"*40)
            
            choice = input("اختر رقم العملية: ").strip()
            
            if choice == "1":
                active_ids = menu_scan(arm)
            elif choice == "2":
                if not active_ids:
                    active_ids = menu_scan(arm)
                menu_live_monitor(arm, active_ids)
            elif choice == "3":
                if not active_ids:
                    active_ids = menu_scan(arm)
                menu_wiggle_test(arm, active_ids)
            elif choice == "4":
                if not active_ids:
                    active_ids = [1, 2, 3, 4, 5, 6]
                arm.set_all_torque(active_ids, False)
                print("[✓] تم إلغاء العزم - يمكنك تحريك الذراع بيدك بحرية.")
            elif choice == "5":
                if not active_ids:
                    active_ids = [1, 2, 3, 4, 5, 6]
                arm.set_all_torque(active_ids, True)
                print("[✓] تم تفعيل العزم - تم تثبيت موضع المحركات.")
            elif choice == "6":
                menu_program_id(arm)
            elif choice == "0":
                print("مع السلامة!")
                break
            else:
                print("[!] خيار غير صالح، يرجى المحاولة مرة أخرى.")

    finally:
        arm.close()

if __name__ == "__main__":
    main()