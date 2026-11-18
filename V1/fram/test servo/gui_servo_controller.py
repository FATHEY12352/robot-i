import customtkinter as ctk
import serial
import serial.tools.list_ports
import time
import threading

class ServoControllerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("برنامج التحكم في السيرفو - PCA9685")
        self.geometry("600x500")
        
        # اعدادات الثيم
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.serial_port = None
        self.is_connected = False
        
        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. إطار الاتصال
        self.conn_frame = ctk.CTkFrame(self)
        self.conn_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        self.port_var = ctk.StringVar(value="اختر البورت")
        self.port_dropdown = ctk.CTkComboBox(self.conn_frame, variable=self.port_var, values=self.get_ports())
        self.port_dropdown.pack(side="left", padx=10, pady=10)
        
        self.refresh_btn = ctk.CTkButton(self.conn_frame, text="تحديث", command=self.refresh_ports, width=60)
        self.refresh_btn.pack(side="left", padx=10, pady=10)
        
        self.connect_btn = ctk.CTkButton(self.conn_frame, text="اتصال", command=self.toggle_connection, fg_color="green")
        self.connect_btn.pack(side="right", padx=10, pady=10)

        # 2. إطار التحكم
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.grid(row=1, column=0, padx=20, pady=0, sticky="ew")
        
        # اختيار القناة
        self.channel_label = ctk.CTkLabel(self.control_frame, text="القناة (Channel):", font=("Arial", 14, "bold"))
        self.channel_label.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        
        self.channel_var = ctk.StringVar(value="1")
        # القنوات المتاحة من 1 إلى 15 (استبعاد القناة 0 بناءً على طلبك)
        channels = [str(i) for i in range(1, 16)]
        self.channel_dropdown = ctk.CTkComboBox(self.control_frame, variable=self.channel_var, values=channels, width=80)
        self.channel_dropdown.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        # شريط التمرير (الزاوية)
        self.angle_label = ctk.CTkLabel(self.control_frame, text="الزاوية (Angle):", font=("Arial", 14, "bold"))
        self.angle_label.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        
        self.angle_slider = ctk.CTkSlider(self.control_frame, from_=0, to=180, number_of_steps=180, command=self.on_angle_change)
        self.angle_slider.set(90) # الوضع الافتراضي
        self.angle_slider.grid(row=1, column=1, padx=10, pady=10, sticky="we")
        
        self.angle_val_label = ctk.CTkLabel(self.control_frame, text="90°", font=("Arial", 14))
        self.angle_val_label.grid(row=1, column=2, padx=10, pady=10, sticky="w")
        
        # زر الحركة التسلسلية
        self.seq_btn = ctk.CTkButton(self.control_frame, text="حركة تسلسلية (1, 2, 3, 7)", command=self.start_sequence, fg_color="#E67E22")
        self.seq_btn.grid(row=2, column=0, columnspan=3, pady=15)

        self.control_frame.grid_columnconfigure(1, weight=1)

        # 3. إطار السجل (Log)
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.grid(row=2, column=0, padx=20, pady=20, sticky="nsew")
        
        self.log_label = ctk.CTkLabel(self.log_frame, text="سجل الرسايل (Log):", font=("Arial", 12))
        self.log_label.pack(anchor="w", padx=10, pady=(10,0))
        
        self.log_textbox = ctk.CTkTextbox(self.log_frame)
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=10)
        self.log_textbox.configure(state="disabled")
        
        # Disable controls initially
        self.set_controls_state("disabled")
        
        # Timer reading serial
        self.after(100, self.read_serial)

    def log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def get_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports] if ports else ["لا توجد منافذ"]

    def refresh_ports(self):
        ports = self.get_ports()
        self.port_dropdown.configure(values=ports)
        if ports and ports[0] != "لا توجد منافذ":
            self.port_var.set(ports[0])
        else:
            self.port_var.set("اختر البورت")

    def toggle_connection(self):
        if not self.is_connected:
            port = self.port_var.get()
            if port == "اختر البورت" or port == "لا توجد منافذ":
                self.log("❌ يرجى اختيار بورت صحيح!")
                return
            try:
                self.serial_port = serial.Serial(port, 9600, timeout=0)
                self.is_connected = True
                self.connect_btn.configure(text="فصل", fg_color="red")
                self.set_controls_state("normal")
                self.log(f"✅ تم الاتصال بنجاح بالمنفذ {port}!")
                # انتظار الأردوينو يعمل ريستارت
                time.sleep(1.5)
            except Exception as e:
                self.log(f"❌ خطأ في الاتصال: {e}")
        else:
            if self.serial_port:
                self.serial_port.close()
            self.is_connected = False
            self.connect_btn.configure(text="اتصال", fg_color="green")
            self.set_controls_state("disabled")
            self.log("🔌 تم فصل الاتصال.")

    def set_controls_state(self, state):
        self.channel_dropdown.configure(state=state)
        self.angle_slider.configure(state=state)
        self.seq_btn.configure(state=state)

    def on_angle_change(self, value):
        angle = int(value)
        self.angle_val_label.configure(text=f"{angle}°")
        
        # إلغاء المؤقت القديم لو لسه بيحرك
        if hasattr(self, 'slider_timer') and self.slider_timer:
            self.after_cancel(self.slider_timer)
            
        # تشغيل المؤقت الجديد (يبعت الأمر بعد ما يوقف تحريك بـ 50 ملي ثانية)
        self.slider_timer = self.after(50, self.send_angle, angle)

    def send_angle(self, angle):
        if self.is_connected and self.serial_port:
            channel = self.channel_var.get()
            command = f"{channel},{angle}\n"
            try:
                self.serial_port.write(command.encode('utf-8'))
            except Exception as e:
                self.log(f"❌ خطأ في الإرسال: {e}")
                self.toggle_connection()

    def start_sequence(self):
        if not self.is_connected:
            self.log("❌ يرجى الاتصال أولاً!")
            return
        self.seq_btn.configure(state="disabled")
        threading.Thread(target=self.run_sequence, daemon=True).start()

    def run_sequence(self):
        self.log("🎬 بدء الحركة التسلسلية للقنوات (1, 2, 3, 7)...")
        sequence_channels = [1, 2, 3, 8]
        try:
            # الحركة الأولى: 45 درجة
            for ch in sequence_channels:
                self.send_direct_angle(ch, 45)
                time.sleep(0.8) # الانتظار قليلاً ليأخذ حركته الناعمة
            time.sleep(1)
            # الحركة الثانية: 135 درجة
            for ch in sequence_channels:
                self.send_direct_angle(ch, 135)
                time.sleep(0.8)
            time.sleep(1)
            # العودة للوضع الطبيعي: 90 درجة
            for ch in sequence_channels:
                self.send_direct_angle(ch, 90)
                time.sleep(0.8)
            self.log("✅ انتهت الحركة التسلسلية.")
        except Exception as e:
            self.log(f"❌ خطأ في التسلسل: {e}")
        finally:
            self.seq_btn.configure(state="normal")

    def send_direct_angle(self, channel, angle):
        if self.is_connected and self.serial_port:
            command = f"{channel},{angle}\n"
            try:
                self.serial_port.write(command.encode('utf-8'))
            except Exception:
                pass

    def read_serial(self):
        if self.is_connected and self.serial_port:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                    if data:
                        if data.startswith("SEL:"):
                            parts = data.split(":")
                            if len(parts) == 2:
                                ch = parts[1]
                                self.channel_var.set(ch)
                                self.log(f"🔘 [HW-040]: تم اختيار القناة {ch}")
                        elif data.startswith("UPD:"):
                            parts = data.split(":")
                            if len(parts) == 3:
                                ch = parts[1]
                                ang = int(parts[2])
                                self.channel_var.set(ch)
                                self.angle_slider.set(ang)
                                self.angle_val_label.configure(text=f"{ang}°")
                                self.log(f"🔄 [HW-040]: القناة {ch} -> {ang}°")
                        else:
                            self.log(f"[الأردوينو]: {data}")
            except Exception as e:
                pass # تجاهل الأخطاء أثناء القراءة عشان ميهنجش الواجهة
        self.after(50, self.read_serial)

if __name__ == "__main__":
    app = ServoControllerApp()
    app.mainloop()
