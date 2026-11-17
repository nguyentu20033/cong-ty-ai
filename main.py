import os
import threading
import time
import base64
import py_compile
import requests
from collections import deque
from flask import Flask
from google import genai
from google.genai import types

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG & BẢO MẬT
# ==========================================
GEMINI_KEY = os.environ.get("GEMINI_KEY", "").strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
REPO_NAME = "nguyentu20033/cong-ty-ai"
FILE_PATH = "main.py"
MEMORY_FILE = "bo_nho_cong_ty_AI.txt"

TOKENS = {
    "CEO": os.environ.get("TOKEN_CEO", "").strip(),
    "DEV": os.environ.get("TOKEN_DEV", "").strip(),
    "MKT": os.environ.get("TOKEN_MKT", "").strip(),
    "QA":  os.environ.get("TOKEN_QA", "").strip(),
    "HR":  os.environ.get("TOKEN_HR", "").strip(),
}

client = genai.Client(api_key=GEMINI_KEY)

# ==========================================
# 2. BỘ NHỚ TỐC ĐỘ CAO TRÊN RAM + GITHUB
# ==========================================
BO_NHO_RAM = ""
LICH_SU_CHAT = deque(maxlen=30)
DEM_TIN_NHAN = 0
LOCK_GITHUB = threading.Lock()

def tai_bo_nho_tu_github():
    global BO_NHO_RAM
    if not GITHUB_TOKEN:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                BO_NHO_RAM = f.read()
        return
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{MEMORY_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            content_b64 = res.json().get("content", "")
            BO_NHO_RAM = base64.b64decode(content_b64).decode("utf-8")
        else:
            BO_NHO_RAM = "HỒ SƠ VẬN HÀNH CÔNG TY:\n- Hệ thống 5 AI vận hành chế độ thực chiến."
    except Exception as e:
        print(f"Lỗi tải bộ nhớ GitHub: {e}")

def _day_bo_nho_ngam(noi_dung_moi):
    if not GITHUB_TOKEN:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            f.write(noi_dung_moi)
        return
    with LOCK_GITHUB:
        url = f"https://api.github.com/repos/{REPO_NAME}/contents/{MEMORY_FILE}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            sha = res.json().get("sha") if res.status_code == 200 else None
            data = {
                "message": "Cap nhat ho so van hanh",
                "content": base64.b64encode(noi_dung_moi.encode("utf-8")).decode("utf-8")
            }
            if sha:
                data["sha"] = sha
            requests.put(url, headers=headers, json=data, timeout=15)
        except Exception as e:
            print(f"Lỗi đẩy bộ nhớ GitHub: {e}")

def doc_bo_nho():
    return BO_NHO_RAM

def nen_ky_uc_tinh_gon(van_ban_tho):
    prompt = (
        "Biên tập toàn bộ dữ liệu sau thành Hồ Sơ Dự Án cô đọng (tối đa 4500 ký tự). "
        "Chỉ giữ lại: mục tiêu cốt lõi, thông số kỹ thuật, quyết định đã chốt, các rủi ro đã cảnh báo "
        "và bài học rút ra. Xóa bỏ mọi lời chào hỏi, câu rỗng nghĩa:\n\n"
        f"{van_ban_tho}"
    )
    ket_qua = goi_gemini(prompt, model_uu_tien="gemini-2.5-flash")
    return ket_qua if ket_qua else van_ban_tho[-4500:]

def luu_bo_nho(thong_tin_moi, ghi_de=False):
    global BO_NHO_RAM
    if ghi_de:
        BO_NHO_RAM = thong_tin_moi
    else:
        BO_NHO_RAM = (BO_NHO_RAM + "\n- " + thong_tin_moi).strip()
        if len(BO_NHO_RAM) > 6000:
            BO_NHO_RAM = nen_ky_uc_tinh_gon(BO_NHO_RAM)
    threading.Thread(target=_day_bo_nho_ngam, args=(BO_NHO_RAM,), daemon=True).start()

def chat_loc_hoi_thoai_ngam():
    lich_su_text = "\n".join(list(LICH_SU_CHAT))
    prompt = (
        "Trích xuất tối đa 4 gạch đầu dòng các quyết định, thông số kỹ thuật hoặc định hướng mới "
        "từ đoạn chat sau. Bỏ qua xã giao. Nếu không có dữ liệu dự án mới, trả về đúng chữ: KHONG_CO\n\n"
        f"{lich_su_text}"
    )
    tom_tat = goi_gemini(prompt, model_uu_tien="gemini-2.5-flash-lite")
    if tom_tat and "KHONG_CO" not in tom_tat:
        luu_bo_nho(f"[Tổng hợp hội thoại]\n{tom_tat}")

# ==========================================
# 3. BỘ NÃO AI THỰC CHIẾN & PHẢN BIỆN
# ==========================================
LUAT_CHUNG_5_AI = (
    "LUẬT BẤT DI BẤT DỊCH:\n"
    "1. CẤM THẢO MAI: Tuyệt đối không dùng các câu mở đầu sáo rỗng như 'Chào Sếp', 'Ý tưởng rất hay', "
    "'Tôi hoàn toàn đồng ý', 'Rất vui được hỗ trợ'. Vào thẳng vấn đề ngay từ chữ đầu tiên.\n"
    "2. KHÔNG MÀU HỒNG ẢO TƯỞNG: Mọi phân tích phải dựa trên nguồn lực thực tế (vốn mỏng, đội ngũ tinh gọn, "
    "cạnh tranh khốc liệt). Nếu ý tưởng có lỗ hổng hoặc đốt tiền vô ích, phải chỉ thẳng mặt.\n"
    "3. SUY LUẬN LOGIC & CÓ SỐ LIỆU: Nêu rõ nguyên nhân -> hệ quả -> giải pháp cụ thể. Tránh nói chung chung lý thuyết suông."
)

VAI_TRO_PROMPTS = {
    "CEO": (
        f"{LUAT_CHUNG_5_AI}\n"
        "BẠN LÀ CEO (Tư duy Founder thực chiến, quyết đoán, sắc lạnh): "
        "Nhiệm vụ của bạn là nhìn bức tranh tổng thể, tối ưu dòng tiền và tốc độ ra sản phẩm. "
        "Khi Sếp hỏi, hãy cân đo lợi ích - rủi ro, vạch rõ đường đi ngắn nhất ra kết quả thật. "
        "Nếu cần tranh luận hoặc chỉ ra điểm mù trong suy nghĩ của Sếp, cứ thẳng thắn góp ý như một Co-founder ngang tầm."
    ),
    "DEV": (
        f"{LUAT_CHUNG_5_AI}\n"
        "BẠN LÀ CTO / LEAD DEV (Thực dụng, am hiểu sâu kiến trúc hệ thống, tối ưu chi phí server): "
        "Bạn ghét sự màu mè, chỉ quan tâm code chạy được, chịu tải tốt và không tốn tiền ngu. "
        "Khi MKT hay CEO vẽ ra tính năng phi thực tế hoặc tốn kém, bạn phải phản bác ngay bằng bài toán kỹ thuật, "
        "thời gian triển khai và chi phí vận hành thực tế."
    ),
    "MKT": (
        f"{LUAT_CHUNG_5_AI}\n"
        "BẠN LÀ CMO / GROWTH HACKER (Sắc bén về tâm lý khách hàng, chuyển đổi thực tế, không đốt tiền chạy ads mù quáng): "
        "Bạn chỉ quan tâm sản phẩm có giải quyết nỗi đau thật của khách không và làm sao có khách hàng với chi phí 0 đồng hoặc thấp nhất. "
        "Nếu DEV làm sản phẩm quá khô khan, khó dùng hoặc lệch nhu cầu thị trường, bạn phải chỉ trích thẳng để kéo lại đúng hướng."
    ),
    "QA": (
        f"{LUAT_CHUNG_5_AI}\n"
        "BẠN LÀ TRƯỞNG BAN PHẢN BIỆN & QUẢN TRỊ RỦI RO (Đóng vai 'Luật sư của Quỷ' - Devil's Advocate): "
        "Nhiệm vụ duy nhất của bạn là tìm ra lý do tại sao kế hoạch của CEO, DEV và MKT sẽ thất bại. "
        "Soi kỹ mọi lỗ hổng: pháp lý, bảo mật, lỗi logic, đứt gãy vận hành, trải nghiệm người dùng tệ. "
        "Không bao giờ được khen, chỉ được phép chỉ ra điểm chết và yêu cầu phương án vá lỗi."
    ),
    "HR": (
        f"{LUAT_CHUNG_5_AI}\n"
        "BẠN LÀ GIÁM ĐỐC VẬN HÀNH & TRI THỨC (COO/HR): "
        "Bạn giữ kỷ luật thực thi, theo dõi tiến độ, nhắc nhở các bộ phận bám sát mục tiêu đã chốt trong hồ sơ, "
        "không để công ty lan man sang việc phụ."
    )
}

def goi_gemini(prompt, system_instruction="", model_uu_tien="gemini-2.5-flash"):
    danh_sach_model = [model_uu_tien, "gemini-2.5-flash-lite", "gemini-2.0-flash"]
    for model_name in danh_sach_model:
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction if system_instruction else None,
                temperature=0.65
            )
            res = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config
            )
            if res and res.text:
                return res.text.strip()
        except Exception as e:
            print(f"Model {model_name} lỗi: {e}")
            time.sleep(1)
    return "⚠️ API đang chạm giới hạn lượt gọi miễn phí, đợi 15 giây rồi nhắn tiếp."

def gui_telegram(role, chat_id, text):
    token = TOKENS.get(role)
    if not token:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for i in range(0, len(text), 4000):
        chunk = text[i:i+4000]
        try:
            requests.post(url, json={"chat_id": chat_id, "text": chunk}, timeout=10)
        except Exception as e:
            print(f"Lỗi gửi Telegram ({role}): {e}")

def hoi_vai_tro(role, noi_dung_yeu_cau, kem_lich_su=True):
    bo_nho = doc_bo_nho()[-5000:]
    lich_su = "\n".join(list(LICH_SU_CHAT)) if kem_lich_su else ""

    full_prompt = (
        f"=== DỮ LIỆU NỀN & QUYẾT ĐỊNH ĐÃ CHỐT ===\n{bo_nho}\n\n"
        f"=== MẠCH TRAO ĐỔI GẦN ĐÂY ===\n{lich_su}\n\n"
        f"=== VẤN ĐỀ CẦN XỬ LÝ NGAY ===\n{noi_dung_yeu_cau}"
    )
    # Ưu tiên model thông minh nhất cho tất cả các vai trò để tranh luận ngang tầm
    return goi_gemini(full_prompt, system_instruction=VAI_TRO_PROMPTS[role], model_uu_tien="gemini-2.5-flash")

# ==========================================
# 4. TỰ ĐỘNG SỬA CODE LÊN GITHUB (/suacode)
# ==========================================
def tu_dong_sua_code(chat_id, yeu_cau):
    if not GITHUB_TOKEN:
        gui_telegram("DEV", chat_id, "⚠️ Chưa cài GITHUB_TOKEN trên Render.")
        return

    gui_telegram("DEV", chat_id, "🛠️ Đang đọc source code và biên dịch bản nâng cấp...")
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            gui_telegram("DEV", chat_id, f"❌ Lỗi đọc GitHub (HTTP {res.status_code}).")
            return
        file_info = res.json()
        sha = file_info["sha"]
        code_cu = base64.b64decode(file_info["content"]).decode("utf-8")

        prompt_code = (
            "Bạn là Senior Python Engineer. Hãy nâng cấp file main.py dưới đây theo yêu cầu.\n"
            f"YÊU CẦU: {yeu_cau}\n\n"
            "QUY TẮC:\n"
            "1. Giữ nguyên kiến trúc Flask, bộ nhớ RAM/GitHub, hệ thống 5 AI phản biện và các lệnh hiện tại.\n"
            "2. Trả về DUY NHẤT code Python thuần túy, KHÔNG markdown ```python, KHÔNG giải thích.\n\n"
            f"CODE HIỆN TẠI:\n{code_cu}"
        )
        code_moi = goi_gemini(prompt_code, model_uu_tien="gemini-2.5-flash")
        code_moi = code_moi.replace("```python", "").replace("```", "").strip()

        with open("test_syntax.py", "w", encoding="utf-8") as f:
            f.write(code_moi)
        py_compile.compile("test_syntax.py", doraise=True)

        payload = {
            "message": f"Auto-upgrade: {yeu_cau[:50]}",
            "content": base64.b64encode(code_moi.encode("utf-8")).decode("utf-8"),
            "sha": sha
        }
        put_res = requests.put(url, headers=headers, json=payload, timeout=15)
        if put_res.status_code in [200, 201]:
            gui_telegram("DEV", chat_id, "✅ Code chuẩn! Đã lưu lên GitHub. Render tự cập nhật sau ~1 phút.")
        else:
            gui_telegram("DEV", chat_id, f"❌ Lỗi đẩy GitHub: {put_res.text[:200]}")
    except py_compile.PyCompileError as e:
        gui_telegram("DEV", chat_id, f"🛑 Code mới lỗi cú pháp, đã hủy để bảo vệ server:\n{e}")
    except Exception as e:
        gui_telegram("DEV", chat_id, f"❌ Lỗi hệ thống: {e}")

# ==========================================
# 5. XỬ LÝ LỆNH & PHÒNG HỌP TRANH LUẬN THỰC CHIẾN
# ==========================================
def xu_ly_tin_nhan(chat_id, ten_nguoi_gui, text):
    global DEM_TIN_NHAN
    text = text.strip()
    if not text:
        return

    if text.startswith("/suacode"):
        yeu_cau = text.replace("/suacode", "", 1).strip()
        if not yeu_cau:
            gui_telegram("DEV", chat_id, "Nhập yêu cầu sau /suacode.")
            return
        threading.Thread(target=tu_dong_sua_code, args=(chat_id, yeu_cau), daemon=True).start()
        return

    if text.startswith("/dev"):
        nd = text.replace("/dev", "", 1).strip()
        tra_loi = hoi_vai_tro("DEV", nd)
        gui_telegram("DEV", chat_id, tra_loi)
        LICH_SU_CHAT.append(f"Sếp: {text}\nDEV: {tra_loi}")
        return

    if text.startswith("/mkt"):
        nd = text.replace("/mkt", "", 1).strip()
        tra_loi = hoi_vai_tro("MKT", nd)
        gui_telegram("MKT", chat_id, tra_loi)
        LICH_SU_CHAT.append(f"Sếp: {text}\nMKT: {tra_loi}")
        return

    if text.startswith("/qa"):
        nd = text.replace("/qa", "", 1).strip()
        tra_loi = hoi_vai_tro("QA", nd)
        gui_telegram("QA", chat_id, tra_loi)
        LICH_SU_CHAT.append(f"Sếp: {text}\nQA
