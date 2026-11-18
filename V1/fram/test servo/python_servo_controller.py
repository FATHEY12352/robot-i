import serial
import serial.tools.list_ports
import time

def list_available_ports():
    ports = serial.tools.list_ports.comports()
    available_ports = []
    print("المنافذ (Ports) المتاحة:")
    if not ports:
        print("  لا يوجد أي منافذ متصلة.")
        return available_ports
        
    for i, port in enumerate(ports):
        print(f"[{i}] {port.device} - {port.description}")
        available_ports.append(port.device)
    return available_ports

def main():
    print("="*40)
    print("برنامج التحكم في السيرفو عن طريق PCA9685")
    print("="*40)
    
    ports = list_available_ports()
    
    if not ports:
        print("يرجى توصيل الأردوينو والمحاولة مرة أخرى.")
        return

    port_index_str = input("\nأدخل رقم المنفذ المتصل به الأردوينو (مثلاً 0 أو 1): ")
    try:
        port_index = int(port_index_str)
        selected_port = ports[port_index]
    except (ValueError, IndexError):
        print("اختيار غير صحيح، البرنامج سيتوقف.")
        return

    try:
        # فتح الاتصال مع الأردوينو
        print(f"جاري الاتصال بالمنفذ {selected_port}...")
        ser = serial.Serial(selected_port, 9600, timeout=1)
        time.sleep(2)  # انتظار الأردوينو حتى يعمل إعادة تشغيل (Reset)
        
        # قراءة الرسائل الترحيبية من الأردوينو إن وجدت
        while ser.in_waiting:
            print(ser.readline().decode('utf-8').strip())

        print("تم الاتصال بنجاح!")
    except serial.SerialException as e:
        print(f"حدث خطأ أثناء فتح المنفذ {selected_port}:\n{e}")
        return

    print("\n" + "="*40)
    print("طريقة الاستخدام:")
    print("اكتب رقم القناة والزاوية مفصولين بفاصلة (,).")
    print("مثال لضبط القناة 0 على الزاوية 90 اكتب: 0,90")
    print("القنوات المتاحة: من 0 إلى 15")
    print("الزوايا المتاحة: من 0 إلى 180")
    print("للخروج من البرنامج اكتب: exit أو quit")
    print("="*40 + "\n")

    while True:
        try:
            command = input("أدخل الأمر (قناة,زاوية) > ")
            
            if command.lower() in ['exit', 'quit']:
                print("جاري إغلاق البرنامج...")
                break
                
            # التحقق البسيط من شكل الأمر
            parts = command.split(',')
            if len(parts) == 2:
                channel = int(parts[0].strip())
                angle = int(parts[1].strip())
                
                if 0 <= channel <= 15 and 0 <= angle <= 180:
                    # إرسال الأمر للأردوينو
                    send_str = f"{channel},{angle}\n"
                    ser.write(send_str.encode('utf-8'))
                    
                    # انتظار الرد من الأردوينو
                    time.sleep(0.05)
                    while ser.in_waiting:
                        response = ser.readline().decode('utf-8', errors='ignore').strip()
                        print(f"[الأردوينو]: {response}")
                else:
                    print("خطأ: تأكد أن القناة بين 0 و 15 والزاوية بين 0 و 180.")
            else:
                print("صيغة غير صحيحة. يرجى استخدام 'قناة,زاوية' (مثال: 0,90).")
                
        except ValueError:
            print("خطأ: يرجى كتابة أرقام صحيحة فقط.")
        except KeyboardInterrupt:
            print("\nتم مقاطعة البرنامج.")
            break
        except Exception as e:
            print(f"حدث خطأ غير متوقع: {e}")

    # إغلاق الاتصال
    ser.close()
    print("تم إغلاق الاتصال.")

if __name__ == "__main__":
    main()

