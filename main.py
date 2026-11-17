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
FILE_LICH_SU_CHAT = "lich_su_chat.txt"

LICH_SU_CHAT = []

def tai_lich_su_chat():
    global LICH_SU_CHAT
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_LICH_SU_CHAT}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            content_encoded = r.json().get("content", "")
            noi_dung = base64.b64decode(content_encoded).decode("utf-8")
            dong_chat = [line.strip() for line in noi_dung.split("\n") if line.strip()]
            LICH_SU_CHAT = dong_chat[-20:]
    except Exception:
        pass

def luu_lich_su_chat_len_github():
    global LICH_SU_CHAT
    noi_dung = "\n".join(LICH_SU_CHAT)
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_LICH_SU_CHAT}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers)
        sha = r.json().get("sha") if r.status_code == 200 else None
        data = {
            "message": "Update lich su chat",
            "content": base64.b64encode(noi_dung.encode("utf-8")).decode("utf-8")
        }
        if sha:
            data["sha"] = sha
        requests.put(url, json=data, headers=headers)
    except Exception:
        pass

def them_vao_lich_su(cau_chat):
    global LICH_SU_CHAT
    LICH_SU_CHAT.append(cau_chat)
    if len(LICH_SU_CHAT) > 20:
        LICH_SU_CHAT = LICH_SU_CHAT[-20:]
    threading.Thread(target=luu_lich_su_chat_len_github, daemon=True).start()

def doc_bo_nho():
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_BO_NHO}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            content_encoded = r.json().get("content", "")
            return base64.b64decode(content_encoded).decode("utf-8")
    except Exception:
        pass
    return "Chưa có dữ liệu dự án."

def nen_ky_uc_tinh_gon(du_lieu_tho):
    prompt = f"Cô đọng nội dung sau thành BẢN HỒ SƠ Ý CHÍNH (tối đa 1.500 ký tự), chia 4 mục: [MỤC TIÊU] | [ĐÃ CHỐT] | [KỸ THUẬT & MKT] | [RỦI RO CẦN TRÁNH].\nDữ liệu:\n{du_lieu_tho}"
    for m in ["gemini-3.5-flash-lite", "gemini-3.8-flash"]:
        try:
            res = client.models.generate_content(model=m, contents=prompt)
            luu_bo_nho_truc_tiep(res.text)
            return res.text
        except Exception:
            time.sleep(1)
    return du_lieu_tho

def luu_bo_nho_truc_tiep(noi_dung):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_BO_NHO}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None
    
    data = {
        "message": "Update bo nho cong ty AI",
        "content": base64.b64encode(noi_dung.encode("utf-8")).decode("utf-8")
    }
    if sha:
        data["sha"] = sha
    requests.put(url, json=data, headers=headers)

def luu_bo_nho(noi_dung_moi):
    hien_tai = doc_bo_nho()
    tong = f"{hien_tai}\n{noi_dung_moi}" if hien_tai != "Chưa có dữ liệu dự án." else noi_dung_moi
    if len(tong) > 2500:
        nen_ky_uc_tinh_gon(tong)
    else:
        luu_bo_nho_truc_tiep(tong)

def hoi_gemini(vai_tro, noi_dung):
    lich_su_str = "\n".join(LICH_SU_CHAT) if LICH_SU_CHAT else "Chưa có lịch sử."
    prompt = f"Vai trò: {vai_tro}.\nHồ sơ ý chính dự án:\n{doc_bo_nho()[-2500:]}\n\nLịch sử chat gần nhất:\n{lich_su_str}\n\nNhiệm vụ từ Sếp: {noi_dung}\n\nQUY TẮC: Trả lời thẳng vào vấn đề, tối đa 3-4 gạch đầu dòng súc tích (dưới 100 chữ) bằng tiếng Việt."
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

def luu_file_len_github(ten_file, noi_dung, thong_diep="Tao file"):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{ten_file}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None
    data = {
        "message": thong_diep,
        "content": base64.b64encode(noi_dung.encode("utf-8")).decode("utf-8")
    }
    if sha:
        data["sha"] = sha
    res = requests.put(url, json=data, headers=headers)
    return res.status_code in [200, 201]

def bat_github_pages():
    url = f"https://api.github.com/repos/{REPO_NAME}/pages"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            payload = {
                "source": {
                    "branch": "main",
                    "path": "/"
                }
            }
            requests.post(url, json=payload, headers=headers)
    except Exception:
        pass

@bot_ceo.message_handler(commands=['taogame'])
def tao_game(message):
    chat_id = message.chat.id
    raw = message.text.replace('/taogame', '', 1).strip()
    parts = raw.split(None, 1)
    if len(parts) < 2:
        bot_dev.send_message(chat_id, "⚠️ Cú pháp: /taogame <ten_game> <mo_ta>")
        return
    ten_game = parts[0].strip().replace('.html', '')
    mo_ta = parts[1].strip()
    if not GITHUB_TOKEN:
        bot_dev.send_message(chat_id, "⚠️ Chưa cài GITHUB_TOKEN trên Render!")
        return

    bot_dev.send_message(chat_id, f"🎮 Dev đang khởi tạo và viết game 2D '{ten_game}'...")

    prompt_game = f"""Bạn là lập trình viên game HTML5/JS xuất sắc. Hãy viết một game 2D hoàn chỉnh theo mô tả: "{mo_ta}".
Tên file: {ten_game}.html

YÊU CẦU BẮT BUỘC:
1. Gói gọn TOÀN BỘ trong DUY NHẤT 1 file HTML (chứa HTML, CSS trong thẻ <style>, Javascript trong thẻ <script>).
2. Tối ưu hoàn hảo cho màn hình cảm ứng điện thoại (hỗ trợ touch events / nút điều khiển cảm ứng trực quan trên màn hình, responsive toàn màn hình).
3. Tích hợp hiệu ứng âm thanh đầy đủ được tạo bằng Web Audio API (AudioContext) cho các thao tác: bấm nút, nhảy/di chuyển, ăn điểm, thua cuộc/game over. Tuyệt đối không dùng link âm thanh ngoài.
4. Có hệ thống tính điểm số (Score) và điểm cao (High Score).
5. Có màn hình Game Over và nút Chơi lại (Restart) mượt mà.
6. Thiết kế UI/UX hiện đại, màu sắc đẹp mắt.

QUY TẮC PHẢN HỒI:
- Chỉ trả về DUY NHẤT mã nguồn HTML hoàn chỉnh từ <!DOCTYPE html> đến </html>.
- KHÔNG bọc trong markdown code block (không dùng ```html hoặc ```), KHÔNG kèm lời dẫn hay giải thích."""

    code_game = None
    for m in ["gemini-3.8-flash", "gemini-3.5-flash-lite"]:
        try:
            res = client.models.generate_content(model=m, contents=prompt_game)
            text = res.text.strip()
            if text.startswith("```"):
                lines = text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                text = "\n".join(lines).strip()
            code_game = text
            break
        except Exception:
            time.sleep(1)

    if not code_game:
        bot_dev.send_message(chat_id, "❌ Lỗi: AI không phản hồi được mã nguồn game. Vui lòng thử lại sau!")
        return

    ten_file = f"{ten_game}.html"
    if luu_file_len_github(ten_file, code_game, f"Tao game {ten_game}"):
        bat_github_pages()
        link_game = f"https://nguyentu20033.github.io/cong-ty-ai/{ten_file}"
        bot_dev.send_message(
            chat_id,
            f"✅ Game 2D '{ten_game}' đã được Dev đóng gói và xuất bản thành công!\n\n"
            f"🕹️ Link chơi trực tiếp:\n{link_game}\n\n"
            f"📱 Đã tối ưu màn hình cảm ứng điện thoại, hiệu ứng Web Audio API & tính điểm!"
        )
    else:
        bot_dev.send_message(chat_id, "❌ Lỗi khi tải mã nguồn game lên GitHub. Vui lòng kiểm tra lại quyền của GITHUB_TOKEN!")

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
- Chỉ trả về DUY NHẤT mã nguồn Python hoàn chỉnh, KHÔNG bọc trong dấu  hay giải thích gì thêm.
- Giữ nguyên web server Flask, các biến môi trường os.environ.get(...), cơ chế phân quyền và lệnh /suacode.

Code hiện tại:
{code_hien_tai}"""

    for m in ["gemini-3.8-flash", "gemini-3.5-flash-lite"]:
        try:
            res = client.models.generate_content(model=m, contents=prompt_code)
            code_moi = res.text.replace("", "").replace("", "").strip()
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
    noi_dung_bo_nho = doc_bo_nho()
    if noi_dung_bo_nho != "Chưa có dữ liệu dự án.":
        bot_hr.send_message(message.chat.id, f"📂 Dung lượng: {len(noi_dung_bo_nho.encode('utf-8'))} bytes\n\n{noi_dung_bo_nho[-1500:]}")
    else:
        bot_hr.send_message(message.chat.id, "⚠️ Chưa có file bộ nhớ.")

@bot_ceo.message_handler(commands=['dondep'])
def don_dep(message):
    noi_dung_bo_nho = doc_bo_nho()
    if noi_dung_bo_nho != "Chưa có dữ liệu dự án.":
        ban_nen = nen_ky_uc_tinh_gon(noi_dung_bo_nho)
        bot_hr.send_message(message.chat.id, f"✅ Đã nén xong:\n\n{ban_nen}")
    else:
        bot_hr.send_message(message.chat.id, "⚠️ Chưa có file bộ nhớ để dọn dẹp.")

def lay_noi_dung_lenh(text, lenh):
    return text.replace(lenh, '', 1).strip()

@bot_ceo.message_handler(commands=['dev'])
def goi_rieng_dev(message):
    nd = lay_noi_dung_lenh(message.text, '/dev')
    if nd:
        them_vao_lich_su(f"Sếp hỏi Dev: {nd}")
        tl = hoi_gemini('Trưởng phòng Kỹ thuật (Dev)', nd)
        them_vao_lich_su(f"Dev trả lời: {tl}")
        bot_dev.send_message(message.chat.id, f"💻 Dev:\n{tl}")

@bot_ceo.message_handler(commands=['mkt'])
def goi_rieng_mkt(message):
    nd = lay_noi_dung_lenh(message.text, '/mkt')
    if nd:
        them_vao_lich_su(f"Sếp hỏi Marketing: {nd}")
        tl = hoi_gemini('Trưởng phòng Marketing', nd)
        them_vao_lich_su(f"Marketing trả lời: {tl}")
        bot_mkt.send_message(message.chat.id, f"📢 Marketing:\n{tl}")

@bot_ceo.message_handler(commands=['qa'])
def goi_rieng_qa(message):
    nd = lay_noi_dung_lenh(message.text, '/qa')
    if nd:
        them_vao_lich_su(f"Sếp hỏi QA: {nd}")
        tl = hoi_gemini('Chuyên gia Kiểm thử (QA)', nd)
        them_vao_lich_su(f"QA trả lời: {tl}")
        bot_qa.send_message(message.chat.id, f"🔍 QA:\n{tl}")

@bot_ceo.message_handler(commands=['daotao', 'hr'])
def goi_rieng_hr(message):
    nd = message.text.split(' ', 1)[1].strip() if ' ' in message.text else ''
    if nd:
        them_vao_lich_su(f"Sếp hỏi HR: {nd}")
        tl = hoi_gemini("Giám đốc Đào tạo & Thư ký (HR)", nd)
        them_vao_lich_su(f"HR trả lời: {tl}")
        luu_bo_nho(f"[Chỉ thị HR: {nd}]\n{tl}")
        bot_hr.send_message(message.chat.id, f"🧠 Đào tạo (HR) & đã lưu:\n{tl}")

@bot_ceo.message_handler(commands=['hop'])
def hop_toan_cong_ty(message):
    chat_id = message.chat.id
    sk = lay_noi_dung_lenh(message.text, '/hop')
    if not sk: return
    them_vao_lich_su(f"Yêu cầu họp: {sk}")
    ceo = hoi_gemini("CEO chiến lược", f"Chủ trì họp về: '{sk}'. Phân tích ngắn và giao việc.")
    them_vao_lich_su(f"CEO: {ceo}")
    bot_ceo.send_message(chat_id, f"👔 CEO:\n{ceo}")
    time.sleep(2)
    dev = hoi_gemini("Trưởng phòng Dev", f"Từ CEO: '{ceo}', đề xuất kỹ thuật cho: '{sk}'.")
    them_vao_lich_su(f"Dev: {dev}")
    bot_dev.send_message(chat_id, f"💻 Dev:\n{dev}")
    time.sleep(2)
    mkt = hoi_gemini("Trưởng phòng Marketing", f"Từ CEO: '{ceo}', đề xuất triển khai cho: '{sk}'.")
    them_vao_lich_su(f"Marketing: {mkt}")
    bot_mkt.send_message(chat_id, f"📢 Marketing:\n{mkt}")
    time.sleep(2)
    qa = hoi_gemini("Chuyên gia QA", f"Chỉ ra 3 lỗ hổng trong phương án Dev ('{dev}') và MKT ('{mkt}').")
    them_vao_lich_su(f"QA: {qa}")
    bot_qa.send_message(chat_id, f"🔍 QA:\n{qa}")
    time.sleep(2)
    hr = hoi_gemini("Thư ký HR", f"Chốt 3 ý chính cuộc họp '{sk}' và cách sửa lỗi QA ('{qa}').")
    them_vao_lich_su(f"HR: {hr}")
    luu_bo_nho(f"[Cuộc họp: {sk}]\n{hr}")
    bot_hr.send_message(chat_id, f"🧠 HR (Đã lưu):\n{hr}")

@bot_ceo.message_handler(func=lambda message: True)
def lam_viec_voi_ceo(message):
    if not message.text.startswith('/'):
        them_vao_lich_su(f"Sếp: {message.text}")
        tl = hoi_gemini('CEO điều hành trực tiếp của Sếp', message.text)
        them_vao_lich_su(f"CEO: {tl}")
        bot_ceo.send_message(message.chat.id, f"👔 CEO:\n{tl}")

def lang_nghe_telegram():
    tai_lich_su_chat()
    bot_ceo.infinity_polling(timeout=60, long_polling_timeout=60)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    print("Đã xong")
    lang_nghe_telegram()