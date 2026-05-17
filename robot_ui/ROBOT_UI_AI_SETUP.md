# Robot UI AI Setup Notes

## Muc tieu

Tich hop AI agent trong `server.py` vao giao dien robot UI de khi launcher mo giao dien thi AI server cung chay, nguoi dung bam mic tren UI de noi chuyen voi LLM.

## Kien truc hien tai

- UI Flask chay tu `run_app.py` tren port `5000`.
- AI server chay tu `server.py` tren port `5001`.
- Firefox kiosk mo `http://localhost:5000`.
- UI goi AI server qua:
  - `POST http://127.0.0.1:5001/stt` de speech-to-text.
  - `POST http://127.0.0.1:5001/chat` de hoi LLM.
  - `POST http://127.0.0.1:5001/tts` de tao audio tra loi.

## Cac file da thay doi

### `robot_launcher/start_robot_stack.sh`

- Launcher khoi dong AI server truoc khi mo UI.
- AI server ghi log vao:

```bash
/tmp/robot_ai_server.log
```

### `start_ui.sh`

- Khoi dong UI Flask.
- Tu dong set default microphone sang USB webcam:

```bash
alsa_input.usb-Jieli_Technology_USB_Composite_Device-02.mono-fallback
```

- Neu source nay khong ton tai, script tu tim USB mic dau tien co dang `alsa_input.usb`.
- Tu dong set default speaker sang loa man hinh HDMI:

```bash
alsa_output.platform-70030000.hda.hdmi-stereo
```

- Neu sink nay khong ton tai, script tu tim HDMI speaker dau tien co chu `hdmi`.
- Firefox duoc mo bang profile rieng:

```bash
/home/jetson/.mozilla/robot_ui_firefox
```

- Profile nay duoc set de Firefox khong hoi lai quyen microphone moi lan boot:

```js
user_pref("media.navigator.permission.disabled", true);
user_pref("media.navigator.video.enabled", false);
user_pref("media.autoplay.default", 0);
```

- Da bo `--private-window` vi private mode lam quyen mic khong on dinh.

### `static/script.js`

- Neu trinh duyet co `SpeechRecognition` thi dung nhu cu.
- Neu Firefox khong co `SpeechRecognition`, UI dung Web Audio API de ghi am.
- Cach dung mic hien tai:
  - Bam mic lan 1 de bat dau ghi am.
  - Noi.
  - Bam mic lan 2 de dung va gui audio.
- Audio duoc encode thanh WAV (`audio/wav`) roi gui ve `/stt`.
- Khong con gioi han tu dong dung sau 5 giay.

### `server.py`

- Chay AI server tren port mac dinh `5001`, co the doi bang bien moi truong:

```bash
AI_PORT=5001
```

- Bo dependency `flask_cors`, thay bang CORS header truc tiep trong Flask.
- `/stt` nhan file audio WAV va goi Gemini de chuyen speech-to-text tieng Viet.
- `/chat` xu ly cau hoi va goi Gemini LLM.
- `/tts` dung `gTTS` tao file MP3 trong RAM bang `BytesIO`.
- Khi `/stt` nhan audio, server luu file debug:

```bash
/tmp/robot_last_stt_audio
```

## Cach chay

Chay launcher:

```bash
bash /home/jetson/robot_ui/robot_launcher/start_robot_stack.sh
```

Test AI server:

```bash
curl -sS http://127.0.0.1:5001/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"mấy giờ rồi"}'
```

Neu thanh cong se tra ve JSON co `reply`.

## Cach dung tren UI

1. Cam USB webcam/mic.
2. Chay launcher.
3. UI mo tren Firefox kiosk.
4. Vao man hinh voice.
5. Bam mic lan 1 de bat dau ghi am.
6. Noi.
7. Bam mic lan 2 de dung va gui.
8. Cho AI tra loi va phat giong noi.

## Cau hinh mic USB

Danh sach source da thay:

```text
1 alsa_input.usb-Jieli_Technology_USB_Composite_Device-02.mono-fallback
2 alsa_output.platform-sound.analog-stereo.monitor
3 alsa_input.platform-sound.analog-stereo
4 alsa_output.platform-70030000.hda.hdmi-stereo.monitor
```

Mic USB webcam la:

```text
alsa_input.usb-Jieli_Technology_USB_Composite_Device-02.mono-fallback
```

Set thu cong neu can:

```bash
pactl set-default-source "alsa_input.usb-Jieli_Technology_USB_Composite_Device-02.mono-fallback"
```

Kiem tra default source:

```bash
pactl info | grep "Default Source"
```

Luu y: cac source co `.monitor` la monitor cua output, khong phai microphone.

## Cau hinh loa HDMI

Kiem tra danh sach output speaker/sink:

```bash
pactl list short sinks
```

Kiem tra default output hien tai:

```bash
pactl info | grep "Default Sink"
```

Tu danh sach source da thay, monitor cua HDMI la:

```text
alsa_output.platform-70030000.hda.hdmi-stereo.monitor
```

Vay sink output HDMI tuong ung la:

```text
alsa_output.platform-70030000.hda.hdmi-stereo
```

Set thu cong neu can:

```bash
pactl set-default-sink "alsa_output.platform-70030000.hda.hdmi-stereo"
```

Test phat am thanh qua default output:

```bash
speaker-test -t wav -c 2
```

Hoac test bang file TTS neu da co server:

```bash
curl -sS http://127.0.0.1:5001/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Xin chao, day la kiem tra loa HDMI"}' \
  --output /tmp/robot_tts_test.mp3

mpg123 /tmp/robot_tts_test.mp3
```

## Lenh kiem tra loi

Kiem tra AI server co chay khong:

```bash
ps aux | grep server.py | grep -v grep
```

Xem log AI server:

```bash
tail -n 100 /tmp/robot_ai_server.log
```

Kiem tra `/stt` endpoint ton tai:

```bash
curl -sS -X POST http://127.0.0.1:5001/stt
```

Ket qua dung khi khong gui audio:

```json
{"error":"Audio is missing"}
```

Kiem tra file audio UI gui ve server:

```bash
file /tmp/robot_last_stt_audio
aplay /tmp/robot_last_stt_audio
```

Neu `aplay` phat ra tieng minh noi, mic va Firefox da ghi am dung. Neu file im lang hoac nhieu, loi nam o input mic/default source.

## Loi da gap va cach xu ly

### `curl: Failed to connect to 127.0.0.1 port 5001`

Nghia la AI server chua chay hoac bi crash.

Chay truc tiep de xem loi:

```bash
cd /home/jetson/robot_ui
AI_PORT=5001 /usr/bin/python3 server.py
```

### `No module named 'flask_cors'`

Da xu ly bang cach bo dependency `flask_cors` trong `server.py`.

### Firefox bao khong ho tro nhan dien giong noi

Firefox tren Linux/Jetson thuong khong co Web Speech API. Da xu ly bang fallback Web Audio API:

```text
Firefox ghi am WAV -> /stt -> Gemini chuyen thanh text
```

### UI bao "Toi khong nghe ro" hoac "khong co noi dung"

Can kiem tra:

```bash
tail -n 100 /tmp/robot_ai_server.log
file /tmp/robot_last_stt_audio
aplay /tmp/robot_last_stt_audio
```

Neu khong co `/tmp/robot_last_stt_audio`, UI chua gui duoc audio toi `/stt` hoac Firefox dang dung cache JS cu.

Tat Firefox va chay lai:

```bash
pkill firefox
bash /home/jetson/robot_ui/robot_launcher/start_robot_stack.sh
```

## Luu y ve Chromium/Chrome

- Ubuntu 20.04 cua Qengineering tren Jetson Nano khong nen cai Chromium theo cach thong thuong vi co the xung dot Snap.
- Huong dang dung hien tai khong can Chromium/Chrome nua.
- Firefox van chay duoc nho fallback ghi am WAV va server-side STT.

## Tat va khoi dong lai

Tat sach:

```bash
pkill -f firefox
pkill -f "python3 /home/jetson/robot_ui/run_app.py"
pkill -f "python3 /home/jetson/robot_ui/server.py"
```

Chay lai:

```bash
bash /home/jetson/robot_ui/robot_launcher/start_robot_stack.sh
```

Reboot neu can:

```bash
sudo reboot
```

Sau reboot, neu launcher duoc gan vao startup/service thi UI va AI server se tu mo lai. Neu port `5001` khong len sau reboot, can kiem tra service/autostart dang goi launcher nao.
