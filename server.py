from flask import Flask, request, jsonify, abort
from google import genai
from google.genai import types
import os, requests
from datetime import datetime

app = Flask(__name__)

# --- CONFIG ---
API_KEY = os.getenv("AI_KEY")
client = genai.Client(api_key=API_KEY)
SUPABASE_URL = "https://wmnlghduybpmxebngqmd.supabase.co"
SUPABASE_KEY = "sb_publishable_oMxdX_KV-IHC0_-JboPBUA_iaLOKwBF" 
headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

# 🛡️ CHÌA KHÓA TỐI MẬT (Chỉ bác và App biết)
MASTER_TOKEN = "HIEPD5_SECURE_ZONE_2026_a@!" 

@app.before_request
def shield():
    # Chỉ cho phép App chính chủ (User-Agent khớp)
    ua = request.headers.get('User-Agent', '').lower()
    if "hiepd5-client-app" not in ua:
        abort(403)
    
    # Kiểm tra Secret Key trong Header cho tất cả các API
    if request.headers.get("HiepD5-Secret") != MASTER_TOKEN:
        return jsonify({"error": "Forbidden"}), 403

@app.route("/generate", methods=["POST"])
def generate():
    try:
        email = request.form.get('email')
        machine = request.form.get('machine')
        base_bytes = request.files["base"].read()
        ref_bytes = request.files["ref"].read()

        # Dùng Gemini 2.5 Flash chuẩn ID
        res = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=[
                "ArchViz Analysis: Form from Img1, Style from Img2. Output PROMPT: [En], VIETNAMESE: [Vn]",
                types.Part.from_bytes(data=base_bytes, mime_type="image/jpeg"),
                types.Part.from_bytes(data=ref_bytes, mime_type="image/jpeg")
            ]
        )
        return jsonify({"text": res.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/get_user_plan")
def get_user_plan():
    email = request.args.get('email')
    url = f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}"
    data = requests.get(url, headers=headers).json()
    return jsonify(data[0] if data else {"plan": "free", "limit": 5})

# ... Các hàm get_usage giữ nguyên nhưng phải gửi kèm Header khi gọi ...

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
