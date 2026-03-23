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
        if "hiepd5-client-app" not in user_agent:
            abort(403)

@app.route("/")
def home():
    return "AI Prompt Server v1.0.9 (Safe & Gemini 2.0 Enabled)"

# ========================================================
# 🚀 HÀM GENERATE CHÍNH (GEMINI 2.0 FLASH + TỰ TRỪ LƯỢT)
# ========================================================
@app.route("/generate", methods=["POST"])
def generate():
    try:
        # --- 1. KIỂM TRA MẬT MÃ (HEADERS) ---
        secret_key = request.headers.get("HiepD5-Secret")
        # Bác nhớ thay xxxxxxxxx bằng mã bác đã cài dưới Tool nhé
        if secret_key != "HIEPD5RENDERa@":
            return jsonify({"error": "Unauthorized"}), 403

        # --- 2. KIỂM TRA EMAIL & THÔNG TIN MÁY ---
        email = request.form.get('email')
        machine = request.form.get('machine') 
        if not email or "@" not in email:
            return jsonify({"error": "Vui lòng dùng bản Tool 1.0.9 mới nhất!"}), 403

        # --- 3. ĐỌC ẢNH ---
        base_bytes = request.files["base"].read()
        ref_bytes = request.files["ref"].read()

        # --- 4. CẤU HÌNH SYSTEM PROMPT ---
        SYSTEM_PROMPT = """
ROLE: World-class ArchViz Director.
TASK: Analyze Image 1 (FORM) and Image 2 (STYLE). 
OUTPUT: Highly detailed prompt.
FORMAT: 
PROMPT: [English]
VIETNAMESE: [Translation]
"""

        # --- GỌI MODEL AI (ĐÃ SỬA TÊN CHUẨN) ---
        res = client.models.generate_content(
            model="gemini-2.0-flash", # Hiện tại đây là định dạng chuẩn nhất cho bản Flash mới
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

        print(f"--- SUCCESS: {email} ---")
        return jsonify({"text": res.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
