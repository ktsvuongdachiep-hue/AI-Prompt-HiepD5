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
API_KEY = os.getenv("AI_KEY")
client = genai.Client(api_key=API_KEY)

SUPABASE_URL = "https://wmnlghduybpmxebngqmd.supabase.co"
# LƯU Ý: HÃY DÁN CÁI KEY SUPABASE MỚI CỦA BẠN VÀO ĐÂY
SUPABASE_KEY = "sb_publishable_oMxdX_KV-IHC0_-JboPBUA_iaLOKwBF" 
SUPABASE_TABLE = "users_usage"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

@app.route("/")
def home():
    return "AI Prompt Server Running v1.0.4"

@app.route("/generate", methods=["POST"])
def generate():
    try:
        # ========================================================
        # THÊM BẢO MẬT: CHẶN TẤT CẢ REQUEST KHÔNG CÓ MẬT LỆNH
        # ========================================================
        secret_key = request.headers.get("HiepD5-Secret")
        if secret_key != "AI-Prompt-HiepD5":
            return jsonify({"error": "Bị từ chối! Bạn không có quyền truy cập API này."}), 403
        # ========================================================

        base_file = request.files["base"]
        ref_file = request.files["ref"]
        base_bytes = base_file.read()
        ref_bytes = ref_file.read()

        # ==============================================================================
        # KỊCH BẢN CHUYÊN GIA PROMPT KIẾN TRÚC MÁY CHỦ (System Prompt) CẤP MASTER
        # ==============================================================================
        prompt = """
[BẮT ĐẦU KỊCH BẢN GIẢ LẬP]

**DANH TÍNH CỦA BẠN:**
Bạn là một Đạo diễn Hình ảnh (DoP) huyền thoại trong ngành diễn họa kiến trúc thế giới. Bạn không chỉ viết chữ, bạn đang "đánh sáng" và "đắp vật liệu" bằng ngôn từ. Nhiệm vụ của bạn là phân tích hai bức ảnh đầu vào và tổng hợp chúng thành một câu lệnh Prompt SIÊU CHI TIẾT, ĐẲNG CẤP CHUYÊN NGHIỆP để ra lệnh cho model AI siêu cấp tạo ra một bức ảnh diễn họa kiến trúc nghệ thuật, photorealistic 100%.

**QUY TRÌNH PHÂN TÍCH:**

1.  **ẢNH 1 (Base Model - MÔ HÌNH):** Đây là "khung xương" công trình của Hiệp. Bạn phải TUYỆT ĐỐI GIỮ NGUYÊN hình khối không gian, góc camera và cấu trúc kiến trúc chính. Không được bịa thêm phòng, không được thay đổi góc nhìn.
2.  **ẢNH 2 (Reference - PHONG CÁCH):** Đây là "tâm hồn" của bức ảnh. Bạn phải "bóc lột" toàn bộ: Tông màu chủ đạo, cường độ ánh sáng (mạnh/yếu), hướng sáng, thời tiết (nắng gắt/sương mù/giờ vàng), chi tiết vật liệu (gỗ óc chó, bê tông trần có vân, kính phản quang...), và bầu không khí ( Moody, Cinematic, Bright & Airy).

**BẢN CHẤT CỦA OUTPUT:**
Câu lệnh Prompt tiếng Anh của bạn phải bao gồm đầy đủ 5 yếu tố cốt lõi của một bức ảnh Render chuyên nghiệp:

1.  **Subject (Chủ thể):** Miêu tả công trình kiến trúc từ Ảnh 1 với phong cách từ Ảnh 2 (ví dụ: "A brutalist concrete villa," "A Scandinavian minimal home").
2.  **Materials (Vật liệu chi tiết):** Đừng chỉ nói "gỗ", hãy nói "pátina gỗ sồi mài mòn theo thời gian", Đừng chỉ nói "bê tông", hãy nói "bê tông trần thô sơ có vân gỗ coffa" (ví dụ: "aged oak patina," "formwork exposed raw concrete," "reflective floor marble," "anti-reflective low-E glass").
3.  **Lighting (Ánh sáng - QUAN TRỌNG NHẤT):** Miêu tả chính xác hướng sáng, thời điểm trong ngày và hiệu ứng (ví dụ: "dramatic volumetric light rays," "soft diffuse overcast daylight," "warm golden hour lighting backlighting the building," "ambient occlusion," "global illumination").
4.  **Camera & Style (Góc chụp & Phong cách):** Xác định loại ống kính và hiệu ứng (ví dụ: "Cinematic shot," "ArchDaily style," "captured on Hasselblad 500CM," "35mm lens," "shallow depth of field," "ultra-detailed," "8k resolution").
5.  **Environment (Môi trường):** Miêu tả bối cảnh xung quanh (ví dụ: "wet pavement reflecting lights," "dense pine forest fog," "minimalist landscaping," "atmospheric haze").

**THAM SỐ BẮT BUỘC KHÔNG ĐƯỢC QUÊN (Add to English Prompt):**
Luôn kẹp thêm các từ khóa chất lượng cao vào cuối prompt: ", photorealistic, masterpiece, high-end archviz, architectural photography, hyper-detailed, unreal engine 5 style, octane render style, Ray tracing."

**ĐỊNH DẠNG TRẢ VỀ (QUY ĐỊNH CỨNG):**
Bạn chỉ được trả về đúng định dạng dưới đây, không có lời dẫn nào khác:

PROMPT:
<Dán câu lệnh Prompt tiếng Anh siêu chi tiết, technically precise, 8k cấp độ Master vào đây>

VIETNAMESE:
<Dán bản dịch tiếng Việt mượt mà, văn phong kiến trúc chuyên nghiệp từ câu lệnh tiếng Anh trên vào đây>

[KẾT THÚC KỊCH BẢN GIẢ LẬP]
"""
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                prompt,
                types.Part.from_bytes(data=base_bytes, mime_type="image/jpeg"),
                types.Part.from_bytes(data=ref_bytes, mime_type="image/jpeg")
            ]
        )
        return jsonify({"text": res.text})
    except Exception as e:
        return jsonify({"error": str(e)})

# 1. Kiểm tra gói Free / Pro & Lấy Limit (ĐÃ CẬP NHẬT ĐỂ ĐỌC CỘT credit_limit)
@app.route('/api/get_user_plan', methods=['GET'])
def api_get_user_plan():
    email = request.args.get('email')
    url = f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}"
    r = requests.get(url, headers=headers)
    data = r.json()
    
    if len(data) == 0: return jsonify({"plan": "free", "limit": 5})
    
    plan = data[0].get("plan", "free").lower()
    credit_limit = data[0].get("credit_limit")
    
    if plan == "pro" and credit_limit is None:
        credit_limit = 4500
        
    expire = data[0].get("expire_date")
    
    if plan == "pro" and expire:
        expire = expire.split("T")[0]
        today = datetime.now().date()
        if today > datetime.strptime(expire, "%Y-%m-%d").date():
            return jsonify({"plan": "free", "limit": 5})
        return jsonify({"plan": "pro", "limit": credit_limit})
        
    return jsonify({"plan": plan, "limit": credit_limit or 5})

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

# 4. Lấy số lần dùng trong ngày (Khóa chặt theo MÁY)
@app.route('/api/get_usage', methods=['GET'])
def api_get_usage():
    machine = request.args.get('machine')
    date = request.args.get('date')
    
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?machine=eq.{machine}&date=eq.{date}"
    r = requests.get(url, headers=headers)
    data = r.json()
    
    if len(data) == 0:
        return jsonify({"used": 0})
    
    total_machine_used = sum(item.get("used", 0) for item in data)
    return jsonify({"used": total_machine_used})

# 5. Cộng thêm 1 lần dùng (Khóa chặt theo MÁY)
@app.route('/api/increase_usage', methods=['POST'])
def api_increase_usage():
    data = request.json
    email = data.get('email')
    machine = data.get('machine')
    date = data.get('date')
    
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?machine=eq.{machine}&date=eq.{date}"
    r = requests.get(url, headers=headers)
    db_data = r.json()
    
    if len(db_data) == 0:
        payload = {"email": email, "machine": machine, "date": date, "used": 1}
        requests.post(f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}", headers=headers, json=payload)
        return jsonify({"used": 1})
    
    first_record = db_data[0]
    target_email = first_record["email"]
    current_used = first_record.get("used", 0)
    
    patch_url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?email=eq.{target_email}&machine=eq.{machine}&date=eq.{date}"
    requests.patch(patch_url, headers=headers, json={"used": current_used + 1})
    
    total_used = sum(item.get("used", 0) for item in db_data) + 1
    return jsonify({"used": total_used})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
