from flask import Flask, request, jsonify, abort
from google import genai
from google.genai import types
import os
import requests
from datetime import datetime

app = Flask(__name__)

# ==========================================
# 🔑 CẤU HÌNH API KEYS & DATABASE
# ==========================================
API_KEY = os.getenv("AI_KEY")
client = genai.Client(api_key=API_KEY)

SUPABASE_URL = "https://wmnlghduybpmxebngqmd.supabase.co"
SUPABASE_KEY = "sb_publishable_oMxdX_KV-IHC0_-JboPBUA_iaLOKwBF" 
SUPABASE_TABLE = "users_usage"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ========================================================
# 🛡️ CHẶN BOT SPAM (BEFORE REQUEST)
# ========================================================
@app.before_request
def block_spam_bots():
    user_agent = request.headers.get('User-Agent', '').lower()
    if request.path == '/generate':
        # Chỉ cho phép hiepd5-client-app (Bản 1.0.9 của bác)
        if "hiepd5-client-app" not in user_agent:
            abort(403)

@app.route("/")
def home():
    return "AI Prompt Server v1.0.9 (Protected & Auto-Update Usage)"

# ========================================================
# 🚀 HÀM GENERATE CHÍNH (ĐÚNG FORM CŨ + TỰ TRỪ LƯỢT)
# ========================================================
@app.route("/generate", methods=["POST"])
def generate():
    try:
        # --- 1. KIỂM TRA MẬT MÃ (HEADERS) ---
        secret_key = request.headers.get("HiepD5-Secret")
        if secret_key != "HIEPD5RENDERa@":
            return jsonify({"error": "Unauthorized"}), 403

        # --- 2. KIỂM TRA EMAIL & THÔNG TIN MÁY (FORM) ---
        email = request.form.get('email')
        machine = request.form.get('machine') 
        if not email or "@" not in email:
            return jsonify({"error": "Vui lòng dùng bản Tool 1.0.9 mới nhất!"}), 403

        # --- 3. ĐỌC ẢNH ---
        base_bytes = request.files["base"].read()
        ref_bytes = request.files["ref"].read()

        # --- 4. CẤU HÌNH SYSTEM PROMPT (MASTER ARCHVIZ) ---
        SYSTEM_PROMPT = """
ROLE: You are a world-class architectural visualization director (DoP).
TASK: Analyze Image 1 (Base Model) for FORM/GEOMETRY and Image 2 (Reference) for STYLE/LIGHTING.

PROCESS:
1. Identify building type and camera angle from Image 1. Preserve original design.
2. Extract lighting (time of day), materials, and mood from Image 2.
3. Synthesize: Apply STYLE from Image 2 onto the FORM of Image 1.

OUTPUT FORMAT (STRICT):
PROMPT: <Highly detailed English prompt including Subject, Materials, Lighting, Camera, Environment>
VIETNAMESE: <Professional Vietnamese translation>

QUALITY TAGS: photorealistic, masterpiece, high-end archviz, hyper-detailed, unreal engine 5 style, octane render style, ray tracing.
"""

        res = client.models.generate_content(
            model="Gemini 2.5 Flash",
            contents=[
                SYSTEM_PROMPT,
                types.Part.from_bytes(data=base_bytes, mime_type="image/jpeg"),
                types.Part.from_bytes(data=ref_bytes, mime_type="image/jpeg")
            ]
        )
        
        # --- 5. TỰ ĐỘNG TRỪ LƯỢT TRÊN SERVER ---
        try:
            user_url = f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}"
            user_data = requests.get(user_url, headers=headers).json()
            
            plan = "free"
            if len(user_data) > 0:
                plan = user_data[0].get("plan", "free").lower()

            if plan == "pro":
                current_total = user_data[0].get("total_used", 0)
                requests.patch(user_url, headers=headers, json={"total_used": current_total + 1})
            else:
                today = datetime.now().strftime("%Y-%m-%d")
                usage_url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?machine=eq.{machine}&date=eq.{today}"
                usage_data = requests.get(usage_url, headers=headers).json()
                
                if len(usage_data) == 0:
                    requests.post(f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}", headers=headers, 
                                  json={"email": email, "machine": machine, "date": today, "used": 1})
                else:
                    curr_used = usage_data[0].get("used", 0)
                    requests.patch(usage_url, headers=headers, json={"used": curr_used + 1})
        except Exception as db_err:
            print(f"Lỗi DB: {db_err}")

        print(f"--- SUCCESS: {email} | Prompt Delivered ---")
        return jsonify({"text": res.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Giữ nguyên các hàm API phía dưới của bác...
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
