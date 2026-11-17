import os
import time
import base64
import threading
import py_compile
import requests
import telebot
from flask import Flask
from google import genai

# --- 1. WEB SERVER GIỮ KẾT NỐI 24/7 CHO RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Cong ty 5 AI dang hoat dong 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- 2. NẠP KEY & TOKEN TỪ KÉT SẮT RENDER ---
client = genai.Client(api_key=os.environ.get("GEMINI_KEY"))
bot_ceo = telebot.TeleBot(os.environ.get("TOKEN_CEO"))
bot_dev = telebot.TeleBot(os.environ.get("TOKEN_DEV"))
bot_mkt = telebot.TeleBot(os.environ.get("TOKEN_MKT"))
bot_qa  = telebot.TeleBot(os.environ.get("TOKEN_QA"))
bot_hr  = telebot.TeleBot(os.environ.get("TOKEN_HR"))

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_NAME = "nguyentu20033/cong-ty-ai"
FILE_PATH = "main.py"
FILE_BO_NHO = "bo_nho_cong_ty_AI.txt"

def doc_bo_nho():
    if os.path.exists(FILE_BO_NHO):
        with open(FILE_BO_NHO, "r", encoding="utf-8") as f:
            return f.read()
    return "Chưa có dữ liệu dự án."

def nen_ky_uc_tinh_gon(du_lieu_tho):
    prompt = f"Cô đọng nội dung sau thành BẢN HỒ SƠ Ý CHÍNH (tối đa 1.500 ký tự), chia 4 mục: [MỤC TIÊU] | [ĐÃ CHỐT] | [KỸ THUẬT & MKT] | [RỦI RO CẦN TRÁNH].\nDữ liệu:\n{du_lieu_tho}"
    for m in ["gemini-3.5-flash-lite", "gemini-3.8-flash"]:
        try:
            res = client.models.generate_content(model=m, contents=prompt)
            with open(FILE_BO_NHO, "w", encoding="utf-8") as f:
                f.write(res.text)
            return res.text
        except Exception:
            time.sleep(1)
    return du_lieu_tho

def luu_bo_nho(noi_dung_moi):
    tong = f"{doc_bo_nho()}\n{noi_dung_moi}"
    if len(tong) > 2500:
        nen_ky_uc_tinh_gon(tong)
    else:
        with open(FILE_BO_NHO, "a", encoding="utf-8") as f:
            f.write(f"\n{noi_dung_moi}")

def hoi_gemini(vai_tro, noi_dung):
    prompt = f"Vai trò: {vai_tro}.\nHồ sơ ý chính dự án:\n{doc_bo_nho()[-2500:]}\n\nNhiệm vụ từ Sếp: {noi_dung}\n\nQUY TẮC: Trả lời thẳng vào vấn đề, tối đa 3-4 gạch đầu dòng súc tích (dưới 100 chữ) bằng tiếng Việt."
    for m in ["gemini-3.5-flash-lite", "gemini-3.8-flash"]:
        try:
            return client.models.generate_content(model=m, contents=prompt).text
        except Exception:
            time.sleep(1)
    return "Máy chủ AI đang bận, vui lòng thử lại sau 5 giây."

def day_code_len_github(code_moi, thong_diep="AI tu nang cap code"):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    sha = r.json().get("sha")
    data = {
        "message": thong_diep,
        "content": base64.b64encode(code_moi.encode("utf-8")).decode("utf-8"),
        "sha": sha
    }
    res = requests.put(url, json=data, headers=headers)
    return res.status_code in [200, 201]

@bot_ceo.message_handler(commands=['suacode'])
def tu_sua_code(message):
    chat_id = message.chat.id
    yeu_cau = message.text.replace('/suacode', '').strip()
    if not yeu_cau:
        bot_dev.send_message(chat_id, "⚠️ Nhập yêu cầu sau lệnh /suacode")
        return
    if not GITHUB_TOKEN:
        bot_dev.send_message(chat_id, "⚠️ Chưa cài GITHUB_TOKEN trên Render!")
        return

    bot_dev.send_message(chat_id, "🛠️ Dev đang đọc mã nguồn và viết bản nâng cấp...")
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        code_hien_tai = f.read()

    prompt_code = f"""Bạn là kỹ sư Python cao cấp. Hãy sửa đoạn code Python dưới đây theo yêu cầu: "{yeu_cau}".
YÊU CẦU NGHIÊM NGẶT:
- Chỉ trả về DUY NHẤT mã nguồn Python hoàn chỉnh, KHÔNG bọc trong dấu ```python hay giải thích gì thêm.
- Giữ nguyên web server Flask, các biến môi trường os.environ.get(...), cơ chế phân quyền và lệnh /suacode.

Code hiện tại:
{code_hien_tai}"""

    for m in ["gemini-3.8-flash", "gemini-3.5-flash-lite"]:
        try:
            res = client.models.generate_content(model=m, contents=prompt_code)
            code_moi = res.text.replace("```python", "").replace("```", "").strip()
            with open("test_temp.py", "w", encoding="utf-8") as f:
                f.write(code_moi)
            py_compile.compile("test_temp.py", doraise=True)
            os.remove("test_temp.py")

            if day_code_len_github(code_moi, f"Update: {yeu_cau[:40]}"):
                bot_dev.send_message(chat_id, "✅ Code chuẩn! Đã lưu lên GitHub. Render sẽ tự động cập nhật sau ~1 phút!")
            else:
                bot_dev.send_message(chat_id, "❌ Lỗi khi đẩy code lên GitHub, kiểm tra lại GITHUB_TOKEN.")
            return
        except Exception as e:
            if os.path.exists("test_temp.py"):
                os.remove("test_temp.py")
            if m == "gemini-3.5-flash-lite":
                bot_dev.send_message(chat_id, f"❌ Lỗi cú pháp code nên đã hủy cập nhật để bảo vệ hệ thống: {e}")

@bot_ceo.message_handler(commands=['kiemtra'])
def kiem_tra(message):
    if os.path.exists(FILE_BO_NHO):
        bot_hr.send_message(message.chat.id, f"📂 Dung lượng: {os.path.getsize(FILE_BO_NHO)} bytes\n\n{doc_bo_nho()[-1500:]}")
    else:
        bot_hr.send_message(message.chat.id, "⚠️ Chưa có file bộ nhớ.")

@bot_ceo.message_handler(commands=['dondep'])
def don_dep(message):
    if os.path.exists(FILE_BO_NHO):
        ban_nen = nen_ky_uc_tinh_gon(doc_bo_nho())
        bot_hr.send_message(message.chat.id, f"✅ Đã nén xong:\n\n{ban_nen}")

def lay_noi_dung_lenh(text, lenh):
    return text.replace(lenh, '', 1).strip()

@bot_ceo.message_handler(commands=['dev'])
def goi_rieng_dev(message):
    nd = lay_noi_dung_lenh(message.text, '/dev')
    if nd: bot_dev.send_message(message.chat.id, f"💻 Dev:\n{hoi_gemini('Trưởng phòng Kỹ thuật (Dev)', nd)}")

@bot_ceo.message_handler(commands=['mkt'])
def goi_rieng_mkt(message):
    nd = lay_noi_dung_lenh(message.text, '/mkt')
    if nd: bot_mkt.send_message(message.chat.id, f"📢 Marketing:\n{hoi_gemini('Trưởng phòng Marketing', nd)}")

@bot_ceo.message_handler(commands=['qa'])
def goi_rieng_qa(message):
    nd = lay_noi_dung_lenh(message.text, '/qa')
    if nd: bot_qa.send_message(message.chat.id, f"🔍 QA:\n{hoi_gemini('Chuyên gia Kiểm thử (QA)', nd)}")

@bot_ceo.message_handler(commands=['daotao', 'hr'])
def goi_rieng_hr(message):
    nd = message.text.split(' ', 1)[1].strip() if ' ' in message.text else ''
    if nd:
        tl = hoi_gemini("Giám đốc Đào tạo & Thư ký (HR)", nd)
        luu_bo_nho(f"[Chỉ thị HR: {nd}]\n{tl}")
        bot_hr.send_message(message.chat.id, f"🧠 Đào tạo (HR) & đã lưu:\n{tl}")

@bot_ceo.message_handler(commands=['hop'])
def hop_toan_cong_ty(message):
    chat_id = message.chat.id
    sk = lay_noi_dung_lenh(message.text, '/hop')
    if not sk: return
    ceo = hoi_gemini("CEO chiến lược", f"Chủ trì họp về: '{sk}'. Phân tích ngắn và giao việc.")
    bot_ceo.send_message(chat_id, f"👔 CEO:\n{ceo}")
    time.sleep(2)
    dev = hoi_gemini("Trưởng phòng Dev", f"Từ CEO: '{ceo}', đề xuất kỹ thuật cho: '{sk}'.")
    bot_dev.send_message(chat_id, f"💻 Dev:\n{dev}")
    time.sleep(2)
    mkt = hoi_gemini("Trưởng phòng Marketing", f"Từ CEO: '{ceo}', đề xuất triển khai cho: '{sk}'.")
    bot_mkt.send_message(chat_id, f"📢 Marketing:\n{mkt}")
    time.sleep(2)
    qa = hoi_gemini("Chuyên gia QA", f"Chỉ ra 3 lỗ hổng trong phương án Dev ('{dev}') và MKT ('{mkt}').")
    bot_qa.send_message(chat_id, f"🔍 QA:\n{qa}")
    time.sleep(2)
    hr = hoi_gemini("Thư ký HR", f"Chốt 3 ý chính cuộc họp '{sk}' và cách sửa lỗi QA ('{qa}').")
    luu_bo_nho(f"[Cuộc họp: {sk}]\n{hr}")
    bot_hr.send_message(chat_id, f"🧠 HR (Đã lưu):\n{hr}")

@bot_ceo.message_handler(func=lambda message: True)
def lam_viec_voi_ceo(message):
    if not message.text.startswith('/'):
        bot_ceo.send_message(message.chat.id, f"👔 CEO:\n{hoi_gemini('CEO điều hành trực tiếp của Sếp', message.text)}")

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot_ceo.infinity_polling(timeout=60, long_polling_timeout=60)
