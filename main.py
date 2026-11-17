import os
import time
import threading
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

# --- 2. NẠP KEY & TOKEN TỪ KÉT SẮT MÔI TRƯỜNG RENDER ---
client = genai.Client(api_key=os.environ.get("GEMINI_KEY"))
bot_ceo = telebot.TeleBot(os.environ.get("TOKEN_CEO"))
bot_dev = telebot.TeleBot(os.environ.get("TOKEN_DEV"))
bot_mkt = telebot.TeleBot(os.environ.get("TOKEN_MKT"))
bot_qa  = telebot.TeleBot(os.environ.get("TOKEN_QA"))
bot_hr  = telebot.TeleBot(os.environ.get("TOKEN_HR"))

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
