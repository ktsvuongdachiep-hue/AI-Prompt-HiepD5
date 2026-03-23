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
        # Khớp với User-Agent dưới máy của bác
        if "hiepd5-client-app" not in user_agent:
            abort(403)

@app.route("/")
def home():
    return "AI Prompt Server v1.0.9 (Protected & Gemini 2.5 Flash Active)"

# ========================================================
# 🚀 HÀM GENERATE CHÍNH (SỬ DỤNG GEMINI 2.5 FLASH)
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
            return jsonify({"error": "Vui lòng đăng nhập lại!"}), 403

        # --- 3. ĐỌC ẢNH ---
        if 'base' not in request.files or 'ref' not in request.files:
            return jsonify({"error": "Thiếu dữ liệu ảnh"}), 400
            
        base_bytes = request.files["base"].read()
        ref_bytes = request.files["ref"].read()

        # --- 4. CẤU HÌNH SYSTEM PROMPT (MASTER ARCHVIZ) ---
        SYSTEM_PROMPT = """
ROLE: World-class architectural visualization director.
TASK: Analyze Image 1 (Base Model) for FORM and Image 2 (Reference) for STYLE.
OUTPUT FORMAT:
PROMPT: <English Detailed Prompt>
VIETNAMESE: <Vietnamese Translation>
"""

        # --- 5. GỌI MODEL GEMINI 2.5 FLASH (TÊN CHUẨN API) ---
        res = client.models.generate_content(
            model="gemini-2.5-flash", # Bác dùng đúng tên này để khớp với Dashboard ảnh 18
            contents=[
                SYSTEM_PROMPT,
                types.Part.from_bytes(data=base_bytes, mime_type="image/jpeg"),
                types.Part.from_bytes(data=ref_bytes, mime_type="image/jpeg")
            ]
        )
        
        # --- 6. TỰ ĐỘNG TRỪ LƯỢT TRÊN SUPABASE ---
        try:
            # Kiểm tra xem user có trong bảng users không
            user_url = f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}"
            user_response = requests.get(user_url, headers=headers)
            user_data = user_response.json()
            
            plan = "free"
            if user_data and len(user_data) > 0:
                plan = user_data[0].get("plan", "free").lower()

            if plan == "pro" or plan == "admin":
                # Tài khoản trả phí hoặc admin: Cộng vào total_used trong bảng users
                current_total = user_data[0].get("total_used", 0)
                requests.patch(user_url, headers=headers, json={"total_used": current_total + 1})
            else:
                # Tài khoản FREE: Cộng vào bảng users_usage theo ngày
                today = datetime.now().strftime("%Y-%m-%d")
                usage_url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?machine=eq.{machine}&date=eq.{today}"
                usage_data = requests.get(usage_url, headers=headers).json()
                
                if not usage_data or len(usage_data) == 0:
                    requests.post(f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}", headers=headers, 
                                  json={"email": email, "machine": machine, "date": today, "used": 1})
                else:
                    curr_used = usage_data[0].get("used", 0)
                    requests.patch(usage_url, headers=headers, json={"used": curr_used + 1})
        except Exception as db_err:
            print(f"Lỗi Database: {db_err}")

        print(f"--- SUCCESS: {email} | Model: Gemini 2.5 Flash ---")
        return jsonify({"text": res.text})

    except Exception as e:
        # Nếu model 2.5 chưa khả dụng hoàn toàn cho API Key của bác, 
        # Server sẽ báo lỗi cụ thể để bác biết.
        return jsonify({"error": str(e)}), 500

# --- CÁC API PHỤ ĐỂ TOOL LẤY THÔNG TIN ---

@app.route("/api/get_user_plan")
def get_user_plan():
    email = request.args.get('email')
    url = f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}"
    try:
        data = requests.get(url, headers=headers).json()
        if data and len(data) > 0:
            return jsonify(data[0])
        return jsonify({"plan": "free", "limit": 5})
    except:
        return jsonify({"plan": "free", "limit": 5})

@app.route("/api/get_total_used")
def get_total_used():
    email = request.args.get('email')
    url = f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}"
    try:
        data = requests.get(url, headers=headers).json()
        if data and len(data) > 0:
            return jsonify({"used": data[0].get("total_used", 0)})
        return jsonify({"used": 0})
    except:
        return jsonify({"used": 0})

@app.route("/api/get_usage")
def get_usage():
    machine = request.args.get('machine')
    date = request.args.get('date')
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?machine=eq.{machine}&date=eq.{date}"
    try:
        data = requests.get(url, headers=headers).json()
        if data and len(data) > 0:
            return jsonify({"used": data[0].get("used", 0)})
        return jsonify({"used": 0})
    except:
        return jsonify({"used": 0})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
