# دليل التشغيل والإصلاحات — SO-101 Studio V4

## 1. المتطلبات

### Windows
- Windows 10/11 64-bit.
- Python 3.10 أو أحدث؛ يفضّل استخدام إصدار تدعمه نسخة PyTorch وLeRobot المثبتة على الجهاز.
- كابل/محول USB للذراعين ومصدر 12V مناسب للـFeetech STS3215.
- كاميرتا USB: كاميرا مساحة العمل وكاميرا المعصم.
- تعريفات USB/Serial والكاميرات مثبتة.
- بطاقة NVIDIA وCUDA اختيارية للتدريب؛ يمكن استخدام CPU للعمليات الخفيفة، لكن تدريب ACT على CPU بطيء.

### Linux / Raspberry Pi
- Python 3 و`python3-venv` و`python3-pip`.
- OpenCV وV4L2، وصلاحية المستخدم للوصول إلى `/dev/ttyUSB*` أو `/dev/ttyACM*` و`/dev/video*`.
- على Raspberry Pi: استخدم CPU أو مسرّعاً متوافقاً؛ لا تفترض توفر CUDA.
- نفّذ مثلاً: `sudo apt update && sudo apt install -y python3 python3-venv python3-pip libgl1`

## 2. التشغيل على جهاز جديد

1. انسخ مجلد `v4/` إلى الجهاز، ولا تشغّل التطبيق من مجلد مؤقت أو من داخل أرشيف مضغوط.
2. على Windows اضغط مرتين على `start_v4.bat`. وعلى Linux نفّذ:
   ```bash
   chmod +x start_v4.sh
   ./start_v4.sh
   ```
3. ينشئ السكربت `.venv` ويثبت:
   - `customtkinter>=5.2.0`
   - `pyserial>=3.5`
   - `opencv-python>=4.8.0`
   - `pillow>=10.0.0`
   - `packaging>=23.0`
4. ثبّت PyTorch المناسب للمنصة ثم LeRobot `>=0.7.0` إذا لم يكونا مثبتين. يمكن مراجعة الأوامر التي يولدها `EnvManager`، مع اختيار wheel متوافق مع إصدار Python وCUDA الفعليين.
5. افتح البرنامج وانتظر فحص البيئة. ستظهر حالة GPU وLeRobot في الشريط العلوي. عدم وجود GPU لا يمنع فتح الواجهة.
6. صِل مصدر 12V للذراعين قبل اختبار السيرفو. لا تعتمد على طاقة USB وحدها؛ قد تظهر قراءة جهد منخفض أو لا تستجيب السيرفو.
7. من تبويب **Hardware Wizard**:
   - اضغط **Refresh Ports**.
   - اختر منفذ follower ومنفذ leader، أو استخدم **Detect Plugged Port** بعد أخذ snapshot ثم إعادة توصيل الكابل.
   - أدخل هوية كل ذراع. القيم الافتراضية `my_follower` و`my_leader` ويمكن استبدالها بهويات المعايرة.
   - اختبر كل منفذ. يجب أن تظهر IDs المتوقعة، وعند غياب ID سيعرض البرنامج السيرفو المفقود.
8. نفّذ معايرة follower ثم leader من الزرين المخصصين. الأوامر تستخدم `--robot.type=so101_follower` و`--teleop.type=so101_leader`.
9. اختبر **Live Teleop** بحركة بطيئة ومنطقة خالية. استخدم **EMERGENCY STOP** أو أغلق الطرفية عند أي حركة غير متوقعة.
10. اختر فهارس كاميرا Top وWrist واضغط **Preview Both**. المعاينة تعمل في خيط خلفي، وتعود النتيجة للواجهة بأمان، ولا ينبغي أن تجمّد البرنامج.
11. احفظ الإعدادات من **Save Current Hardware Profile**. تحفظ في `config/hardware_profile.json`.
12. من تبويب التسجيل، اكتب وصف المهمة وعدد الحلقات، واترك `push_to_hub` مغلقاً في البداية، ثم ابدأ التسجيل واتبع تعليمات الطرفية.
13. درّب ACT محلياً أو صدّر dataset إلى `exports/` للتدريب السحابي. التدريب المحلي يفرض TF32 ويعطّل AMP.
14. استورد checkpoint من تبويب التدريب. يجب أن يحتوي على `config.json` وملف أوزان (`.safetensors` أو `.bin`).
15. من تبويب Rollout اختر النموذج والجهاز والمهمة، ثم شغّل rollout بعد التأكد من المعايرة ومصدر الطاقة ومنطقة الأمان.

## 3. قواعد أوامر LeRobot

- calibration وrecord وteleoperate تستخدم نوعي العتاد الرسميين:
  - `--robot.type=so101_follower`
  - `--teleop.type=so101_leader`
- `lerobot-record` يستخدم `--dataset.fps` وليس `--fps`، ويضيف `--dataset.single_task` و`--dataset.push_to_hub=false` افتراضياً.
- `lerobot-rollout` يستخدم `--policy.path` فقط عند اختيار checkpoint. لا يمرر التطبيق `--policy.type` معه، حتى لا يحدث تعارض في Draccus/LeRobot.
- Rollout يرسل إعدادات الروبوت والكاميرات والمهمة والجهاز والاستراتيجية و`interpolation_multiplier`.
- تدريب ACT يمرر `--tf32=true` و`--policy.use_amp=false` دائماً. سبب ذلك تقليل عدم الاستقرار وNaN المرتبطين بـAMP في سيناريو المشروع.

## 4. المعايرة والكاميرات والمنافذ

### معايرة LeRobot
يبحث التطبيق في:
- `V4/calibration/`
- `~/.cache/huggingface/lerobot/calibration/`

ويستخدم بحثاً متداخلاً `rglob("*.json")`، لذلك يعمل مع اختلافات بنية المجلدات بين إصدارات LeRobot، بشرط وجود مجلد `so_follower` أو `so_leader` في المسار الأب لملف JSON.

### الكاميرات
- المعاينة تعمل في خيط خلفي منفصل عن واجهة Tk، لذلك فشل أو بطء backend لا يحجب خيط الواجهة. يوجد قفل بمهلة انتظار لمنع معاينات متزامنة للكاميرا نفسها، لكن مهلة OpenCV لا تضمن إيقاف كل تعريف كاميرا عالق.
- إذا لم تفتح الكاميرا، جرّب فهرساً آخر، افصل البرامج الأخرى التي تستخدمها، وتحقق من أذونات `/dev/video*` في Linux.

### المنافذ
- إذا ظهر `Access denied` أو `busy`: أغلق أي LeRobot/Serial Monitor، استخدم **Free Ports**، ثم افصل وأعد توصيل المحول.
- في Linux أضف المستخدم إلى المجموعة المناسبة مثل `dialout` ثم أعد تسجيل الدخول.
- لا تستخدم نفس المنفذ للـleader والـfollower.

## 5. المشاكل التي عولجت

1. **نسخة OpenCV غير متسقة:** تم توحيدها إلى `opencv-python>=4.8.0` كما هو مطلوب، مع بقاء بقية القيود غير مقفولة بإصدارات وهمية.
2. **أسماء LeRobot CLI:** تم تثبيت `so101_follower` و`so101_leader` وعدم استخدام أسماء مجلدات المعايرة كأنها أنواع CLI.
3. **تعارض rollout:** تم منع `--policy.type` عند وجود `--policy.path`.
4. **استقرار ACT:** تم فرض TF32 وتعطيل AMP حتى لو استدعى الكود builder بقيمة `use_amp=True`.
5. **فحص المعايرة الناقص:** استُبدل البحث المباشر ببحث `rglob("*.json")` في cache المحلي ومخبأ Hugging Face.
6. **تجمّد/تعليق الواجهة:** عمليات البيئة والمنافذ والكاليبريشن والنماذج والتقاط الكاميرا تعمل بعيداً عن خيط Tk، وتحديث الwidgets يتم في الخيط الرئيسي.
7. **تداخل معاينتي الكاميرا:** تمت إضافة generation token لمنع نتيجة قديمة من الكتابة فوق طلب أحدث، مع مهلة فتح الكاميرا.
8. **انهيار بسبب إدخال رقمي خاطئ:** أضيف تحويل آمن للفهارس وعدد الحلقات وخطوات التدريب وحجم الدفعة وinterpolation multiplier.
9. **إطلاق Linux:** تم استخدام اقتباس آمن لوسائط الأوامر في الطرفية.
10. **تحرير المنافذ في Windows:** أزيل الاعتماد على wildcard غير مضمون مع `taskkill /IM`؛ يعتمد الإيقاف الآن على أشجار العمليات التي أطلقها التطبيق.

## 6. التحقق وDry-Run

من مجلد `V4`:

```bash
python -m compileall -q app_v4.py core tests
python -c "import sys; sys.path.insert(0, '.'); import app_v4; from core.process_runner import ProcessRunner; print(ProcessRunner().build_rollout_command('dummy'))"
python -m pytest -q
```

- `python -m pytest -q`: **16 passed**. ظهر تحذير pytest واحد من `PytestAssertRewriteWarning` لمكوّن `anyio`، وليس فشلاً في الاختبارات.
- لم يتوفر `bash` على جهاز Windows الحالي؛ لذلك لم يمكن تشغيل `bash -n start_v4.sh` هنا. يظل التحقق الفعلي لملف الإطلاق Linux مطلوباً على Linux/WSL.

## 7. استكشاف الأعطال

- راجع `v4_studio.log` وسجل الطرفية.
- إذا فشل الاستيراد: شغّل `start_v4.bat` أو `start_v4.sh` بدلاً من Python عالمي مختلف.
- إذا فشل LeRobot: تحقق من `python -c "import lerobot; print(lerobot.__version__)"` ومن ظهور `lerobot-record` و`lerobot-rollout` في نفس البيئة.
- إذا فشل GPU: اختر `cpu` في Rollout، ولا تعتبر فشل CUDA خطأً في الواجهة.
- إذا غاب Servo: أوقف الحركة، راجع كابل 3-pin والطاقة والعنوان، ثم أعد الاختبار.
