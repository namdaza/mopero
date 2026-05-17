import os
import base64
import json
import urllib.error
import urllib.request
from flask import Flask, request, jsonify, send_file
from datetime import datetime
from io import BytesIO
from gtts import gTTS
import locale


def load_env_file(path=".env"):
    if not os.path.exists(path):
        return

    with open(path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("Thiếu biến môi trường API_KEY trong file .env")

AI_MODEL = os.getenv("AI_MODEL", "gemini-2.5-flash")
SYSTEM_INSTRUCTION = (
    "Bạn là một trợ lý AI hỗ trợ các điều dưỡng ở viện dưỡng lão, "
    "hãy trả lời ngắn gọn, không dùng markdown, không ký hiệu đặc biệt, "
    "tông giọng nhẹ nhàng."
)

app = Flask(__name__)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

try:
    locale.setlocale(locale.LC_TIME, "vi_VN.UTF-8")
except:
    pass


def get_vietnamese_date():
    weekdays = {
        0: "Thứ Hai", 1: "Thứ Ba", 2: "Thứ Tư", 3: "Thứ Năm",
        4: "Thứ Sáu", 5: "Thứ Bảy", 6: "Chủ Nhật",
    }
    today = datetime.now()
    thu = weekdays[today.weekday()]
    return f"Hôm nay là {thu}, ngày {today.day} tháng {today.month} năm {today.year}"


# Lịch sử hội thoại 
messages = [
    {
        "role": "system",
        "content": "Bạn là một trợ lý AI hỗ trợ các điều dưỡng ở viện dưỡng lão, hãy trả lời ngắn gọn, không markdown, không ký hiệu đặc biệt.",
    }
]

def trim_history(msgs, max_turns=6):
    """Giữ lại system + tối đa max_turns tin nhắn gần nhất."""
    sys = [msgs[0]]
    rest = msgs[1:]
    return sys + rest[-max_turns:]


def ask_gemini(user_text):
    contents = []

    for m in messages[1:]:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    contents.append({"role": "user", "parts": [{"text": user_text}]})

    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": 300,
            "temperature": 0.7,
        },
    }

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{AI_MODEL}:generateContent?key={API_KEY}"
    )
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    parts = (
        result.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    text = "".join(part.get("text", "") for part in parts).strip()
    return text or "Xin lỗi, tôi chưa có câu trả lời phù hợp."


def transcribe_audio(audio_bytes, mime_type):
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "Hãy nghe đoạn âm thanh này và chép lại chính xác "
                            "thành tiếng Việt. Chỉ trả về nội dung người dùng nói."
                        )
                    },
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": base64.b64encode(audio_bytes).decode("ascii"),
                        }
                    },
                ],
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 120,
            "temperature": 0.1,
        },
    }

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{AI_MODEL}:generateContent?key={API_KEY}"
    )
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=45) as response:
        result = json.loads(response.read().decode("utf-8"))

    parts = (
        result.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    return "".join(part.get("text", "") for part in parts).strip()


def process_ai_logic(user_text):
    global messages

    normalized = user_text.lower().strip()
    robot_brain = None

    if any(k in normalized for k in ["xóa lịch sử", "reset", "đổi chủ đề"]):
        messages = messages[:1]
        return "Đã xóa lịch sử. Bạn muốn nói về chủ đề nào?"

    custom_responses = {
        "mấy giờ": lambda: f"Bây giờ là {datetime.now().strftime('%H:%M:%S')}",
        "ngày mấy": get_vietnamese_date,
        "hôm nay": get_vietnamese_date,
        "đau đầu": lambda: "Hãy thử uống một cốc nước ấm và nghỉ ngơi chút nhé.",
    }

    for key, make_resp in custom_responses.items():
        if key in normalized:
            robot_brain = make_resp()
            messages.append({"role": "user", "content": user_text})
            messages.append({"role": "assistant", "content": robot_brain})
            messages = trim_history(messages)
            return robot_brain

    if robot_brain is None:
        try:
            robot_brain = ask_gemini(user_text)

        except Exception as e:
            print("Lỗi Gemini API:", e)
            robot_brain = "Xin lỗi, hệ thống đang gặp sự cố, vui lòng thử lại sau."

        messages.append({"role": "user", "content": user_text})
        messages.append({"role": "assistant", "content": robot_brain})
        messages = trim_history(messages)

    return robot_brain


@app.route('/chat', methods=['POST'])
def chat_endpoint():
    data = request.json
    user_text = data.get('message', '')

    print(f"Nhận từ HTML: {user_text}")

    if not user_text:
        return jsonify({'reply': 'Tôi không nghe rõ.'})

    response_text = process_ai_logic(user_text)

    print(f"Trả về HTML: {response_text}")

    return jsonify({'reply': response_text})


@app.route('/stt', methods=['POST'])
def stt_endpoint():
    audio_file = request.files.get('audio')
    if not audio_file:
        return jsonify({'error': 'Audio is missing'}), 400

    audio_bytes = audio_file.read()
    mime_type = audio_file.mimetype or 'audio/wav'

    if not audio_bytes:
        return jsonify({'error': 'Audio is empty'}), 400

    try:
        with open('/tmp/robot_last_stt_audio', 'wb') as debug_audio:
            debug_audio.write(audio_bytes)
        print(f"STT audio: {len(audio_bytes)} bytes, mime={mime_type}")
        text = transcribe_audio(audio_bytes, mime_type)
        print(f"STT: {text}")
        return jsonify({'text': text})
    except Exception as e:
        print("Lỗi STT:", e)
        return jsonify({'error': 'STT failed'}), 500


@app.route('/tts', methods=['POST'])
def tts_endpoint():
    data = request.json or {}
    text = (data.get('text') or '').strip()

    if not text:
        return jsonify({'error': 'Text is empty'}), 400

    try:
        mp3_buffer = BytesIO()
        tts = gTTS(text=text, lang='vi', tld='com.vn')
        tts.write_to_fp(mp3_buffer)
        mp3_buffer.seek(0)

        return send_file(
            mp3_buffer,
            mimetype='audio/mpeg',
            as_attachment=False,
            download_name='reply.mp3'
        )
    except Exception as e:
        print('Lỗi TTS:', e)
        return jsonify({'error': 'TTS failed'}), 500


if __name__ == '__main__':
    port = int(os.environ.get("AI_PORT", "5001"))
    print(f"AI server đang chạy tại http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
