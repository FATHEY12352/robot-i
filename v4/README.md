# SO-101 Robotics Studio V4

واجهة مكتبية لتجهيز ذراع SO-101 ومعايرته، جمع بيانات العرض، تدريب ACT، وتجربة سياسة مدرّبة عبر LeRobot.

> **تنبيه سلامة:** اختبر أولاً دون حمل وبسرعة/منطقة آمنة. استخدم مصدر 12V مناسباً للسيرفو. Dry-Run لا يحرّك الذراع؛ فهو يفحص تركيب أوامر CLI فقط.

## الوظائف
- معالج عتاد: اكتشاف منافذ Serial، اختبار السيرفو، فحص الكاليبريشن، ومعاينة كاميرتي Top وWrist.
- جمع الحلقات باستخدام `lerobot-record` مع وصف المهمة والكاميرات.
- تدريب ACT محلياً أو تجهيز dataset للتدريب السحابي، مع فحص واستيراد checkpoint.
- تشغيل `lerobot-rollout` مع إيقاف طارئ.

## التشغيل السريع
### Windows
1. ثبّت Python 3.10+ 64-bit بإضافة Python إلى PATH.
2. شغّل `start_v4.bat`.

### Linux / Raspberry Pi
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip libgl1
chmod +x start_v4.sh
./start_v4.sh
```

ينشئ المشغّل `.venv` ويثبت متطلبات الواجهة. ثبّت PyTorch المناسب وLeRobot `>=0.7.0` في البيئة نفسها. اختيار إصدار PyTorch/CUDA يعتمد على نظام التشغيل والبطاقة وإصدار Python؛ Raspberry Pi يعمل عادةً CPU ولا ينبغي افتراض توفر CUDA.

## إعداد الذراع وتشغيله
1. صِل الذراع بمصدر 12V وكابل USB، ثم افتح تبويب **Hardware Wizard**.
2. حدّد منافذ follower وleader. لا تستخدم المنفذ نفسه للذراعين.
3. اختبر المنفذين، وتأكد من استجابة السيرفو IDs المتوقعة. عالج أي ID مفقود أو جهد منخفض قبل الحركة.
4. عاير follower ثم leader من داخل البرنامج.
5. عاين الكاميرتين وحدد فهرسي Top وWrist، ثم احفظ Hardware Profile.
6. اختبر Live Teleop بحذر. اجعل منطقة الحركة خالية واستخدم Emergency Stop عند الحاجة.
7. سجّل بيانات مع وصف مهمة واضح وعدد حلقات مناسب. اترك رفع Hugging Face مغلقاً ما لم تكن تريد الرفع.
8. درّب ACT محلياً أو صدّر dataset؛ استورد checkpoint صالحاً ثم شغّل Rollout بعد التحقق من الأمان.

## قواعد توافق LeRobot
- أنواع الذراع في CLI هي `--robot.type=so101_follower` و`--teleop.type=so101_leader`.
- التسجيل يمرر `--dataset.fps`، ووصف `--dataset.single_task`، مع `--dataset.push_to_hub=false` افتراضياً.
- Rollout يعتمد `--policy.path` ولا يمرر `--policy.type` معه.
- تدريب ACT يفرض `--tf32=true` و`--policy.use_amp=false`.
- يبحث التطبيق عن ملفات المعايرة باستخدام `rglob("*.json")` في `V4/calibration/` ومخبأ `~/.cache/huggingface/lerobot/calibration/`.

## فحوصات المطور
من مجلد `V4`:
```bash
python -m compileall -q app_v4.py core tests
python -c "import sys; sys.path.insert(0, '.'); import app_v4; from core.process_runner import ProcessRunner; print(ProcessRunner().build_rollout_command('dummy'))"
python -m pytest -q
```

## توثيق إضافي
- [سجل التغييرات](docs/CHANGELOG.md)
- [دليل التشغيل والأخطاء وحلولها](docs/GUIDE_AND_FIXES.md)
- [خطة العمل وIteration 2](docs/PLAN.md)

**قاعدة صيانة التوثيق:** أي تعديل أو إضافة لاحقة في V4 يجب أن يصاحبه إدخال مؤرخ وملخص في `docs/CHANGELOG.md` في نفس التغيير.
