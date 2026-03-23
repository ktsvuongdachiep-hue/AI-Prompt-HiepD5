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
# Đảm bảo bạn đã set Environment Variable trên Render là AI_KEY
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
        # Chỉ cho phép User-Agent từ App của Hiệp gửi lên
        if "hiepd5-client-app" not in user_agent:
            abort(403)

@app.route("/")
def home():
    return "AI Prompt Server v1.0.9 (Safe & Gemini 2.0 Flash Enabled)"

# ========================================================
# 🚀 HÀM GENERATE CHÍNH (GEMINI 2.0 FLASH + TỰ TRỪ LƯỢT)
# ========================================================
@app.route("/generate", methods=["POST"])
def generate():
    try:
        # --- 1. KIỂM TRA MẬT MÃ (HEADERS) ---
        secret_key = request.headers.get("HiepD5-Secret")
        if secret_key != "hiepd5-client-app2026":
            return jsonify({"error": "Unauthorized"}), 403

        # --- 2. KIỂM TRA EMAIL & THÔNG TIN MÁY ---
        email = request.form.get('email')
        machine = request.form.get('machine') 
        if not email or "@" not in email:
            return jsonify({"error": "Vui lòng dùng bản Tool 1.0.9 mới nhất!"}), 403

        # --- 3. ĐỌC ẢNH TỪ REQUEST ---
        if 'base' not in request.files or 'ref' not in request.files:
            return jsonify({"error": "Thiếu file ảnh gửi lên server!"}), 400
            
        base_bytes = request.files["base"].read()
        ref_bytes = request.files["ref"].read()

        # --- 4. CẤU HÌNH SYSTEM PROMPT (ÉP ĐỊNH DẠNG ĐỂ APP TÁCH CHUỖI) ---
        SYSTEM_PROMPT = """
ROLE: World-class Architectural Visualization (ArchViz) Director.
TASK: Analyze Image 1 (FORM & STRUCTURE) and Image 2 (STYLE, LIGHTING, MATERIALS).
OUTPUT: Create a highly detailed and professional rendering prompt.
STRICT FORMAT: 
[English Prompt Content]
VIETNAMESE: [Bản dịch tiếng Việt chi tiết]
"""

        # --- GỌI MODEL GEMINI 2.0 FLASH ---
        res = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=[
                SYSTEM_PROMPT,
                types.Part.from_bytes(data=base_bytes, mime_type="image/jpeg"),
                types.Part.from_bytes(data=ref_bytes, mime_type="image/jpeg")
            ]
        )
        
        # Kiểm tra kết quả trả về từ AI
        full_text = res.text if res.text else "Lỗi: AI không tạo được nội dung."

        # --- 5. TỰ ĐỘNG TRỪ LƯỢT TRÊN SERVER (SUPABASE) ---
        try:
            user_url = f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}"
            user_res = requests.get(user_url, headers=headers)
            user_data = user_res.json()
            
            plan = "free"
            if isinstance(user_data, list) and len(user_data) > 0:
                plan = user_data[0].get("plan", "free").lower()

            if plan == "pro":
                # Gói PRO: Trừ vào total_used
                current_total = user_data[0].get("total_used", 0)
                requests.patch(user_url, headers=headers, json={"total_used": current_total + 1})
            else:
                # Gói FREE: Tính theo máy (machine) và ngày (date)
                today = datetime.now().strftime("%Y-%m-%d")
                usage_url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?machine=eq.{machine}&date=eq.{today}"
                usage_res = requests.get(usage_url, headers=headers)
                usage_data = usage_res.json()
                
                if isinstance(usage_data, list) and len(usage_data) == 0:
                    # Lượt đầu trong ngày
                    requests.post(f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}", headers=headers, 
                                  json={"email": email, "machine": machine, "date": today, "used": 1})
                else:
                    # Đã có lượt dùng, tăng thêm 1
                    curr_used = usage_data[0].get("used", 0)
                    requests.patch(usage_url, headers=headers, json={"used": curr_used + 1})
        except Exception as db_err:
            print(f"Lỗi DB: {db_err}")
            # Vẫn cho trả kết quả AI về dù lỗi trừ lượt để trải nghiệm người dùng không bị ngắt

        print(f"--- SUCCESS: {email} ---")
        return jsonify({"text": full_text})

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        return jsonify({"error": f"Server Error: {str(e)}"}), 500

# ========================================================
# ⚙️ KHỞI CHẠY SERVER
# ========================================================
if __name__ == "__main__":
    # Render yêu cầu chạy port từ biến môi trường
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
