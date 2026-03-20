from flask import Flask, request, jsonify
from google import genai
from google.genai import types
import os
import requests
from datetime import datetime

app = Flask(__name__)

# ==========================================
# CẤU HÌNH API KEYS
# ==========================================
# Lấy API Gemini từ biến môi trường Render
API_KEY = os.getenv("AI_KEY")
client = genai.Client(api_key=API_KEY)

# Cấu hình Supabase (Đã giấu an toàn trên Server)
SUPABASE_URL = "https://wmnlghduybpmxebngqmd.supabase.co"
SUPABASE_KEY = "sb_publishable_Y12kkCYn5ztL1ai6WJsS8Q_B9_OabYO"
SUPABASE_TABLE = "users_usage"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

# ==========================================
# API LÕI: TẠO PROMPT D5 RENDER (Giữ nguyên)
# ==========================================
@app.route("/")
def home():
    return "AI Prompt Server Running"

@app.route("/generate", methods=["POST"])
def generate():
    try:
        base_file = request.files["base"]
        ref_file = request.files["ref"]

        base_bytes = base_file.read()
        ref_bytes = ref_file.read()

        prompt = """
You are an architectural visualization prompt engineer.

Image1 = building model.
Image2 = render reference.

Return:

PROMPT:
<english>

VIETNAMESE:
<vietnamese>
"""
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                prompt,
                types.Part.from_bytes(
                    data=base_bytes,
                    mime_type="image/jpeg"
                ),
                types.Part.from_bytes(
                    data=ref_bytes,
                    mime_type="image/jpeg"
                )
            ]
        )

        return jsonify({
            "text": res.text
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        })

# ==========================================
# API MỚI: QUẢN LÝ USER & LƯỢT DÙNG (SUPABASE)
# ==========================================

# 1. Kiểm tra gói Free / Pro
@app.route('/api/get_user_plan', methods=['GET'])
def api_get_user_plan():
    email = request.args.get('email')
    url = f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}"
    r = requests.get(url, headers=headers)
    data = r.json()
    
    if len(data) == 0: return jsonify({"plan": "free"})
    
    plan = data[0].get("plan", "free")
    expire = data[0].get("expire_date")
    
    if plan == "pro" and expire:
        expire = expire.split("T")[0]
        today = datetime.now().date()
        if today > datetime.strptime(expire, "%Y-%m-%d").date():
            return jsonify({"plan": "free"})
        return jsonify({"plan": "pro"})
    return jsonify({"plan": "free"})

# 2. Lấy tổng số lần đã dùng (Cho thẻ PRO)
@app.route('/api/get_total_used', methods=['GET'])
def api_get_total_used():
    email = request.args.get('email')
    url = f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}"
    r = requests.get(url, headers=headers)
    data = r.json()
    if len(data) == 0 or data[0].get("total_used") is None:
        return jsonify({"used": 0})
    return jsonify({"used": data[0]["total_used"]})

# 3. Cộng thêm 1 lần dùng (Cho thẻ PRO)
@app.route('/api/increase_total_used', methods=['POST'])
def api_increase_total_used():
    email = request.json.get('email')
    url_get = f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}"
    r_get = requests.get(url_get, headers=headers).json()
    used = 0 if len(r_get) == 0 or r_get[0].get("total_used") is None else r_get[0]["total_used"]
    
    requests.patch(url_get, headers=headers, json={"total_used": used + 1})
    return jsonify({"status": "ok"})

# 4. Lấy số lần dùng trong ngày (Cho thẻ FREE)
@app.route('/api/get_usage', methods=['GET'])
def api_get_usage():
    email = request.args.get('email')
    machine = request.args.get('machine')
    date = request.args.get('date')
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?email=eq.{email}&machine=eq.{machine}&date=eq.{date}"
    
    r = requests.get(url, headers=headers)
    data = r.json()
    
    if len(data) == 0:
        payload = {"email": email, "machine": machine, "date": date, "used": 0}
        requests.post(f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}", headers=headers, json=payload)
        return jsonify({"used": 0})
    return jsonify({"used": data[0]["used"]})

# 5. Cộng thêm 1 lần dùng trong ngày (Cho thẻ FREE)
@app.route('/api/increase_usage', methods=['POST'])
def api_increase_usage():
    data = request.json
    email, machine, date = data.get('email'), data.get('machine'), data.get('date')
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?email=eq.{email}&machine=eq.{machine}&date=eq.{date}"
    
    r = requests.get(url, headers=headers)
    db_data = r.json()
    
    if len(db_data) == 0: return jsonify({"used": 0})
    
    used = db_data[0]["used"] + 1
    requests.patch(url, headers=headers, json={"used": used})
    return jsonify({"used": used})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
