
import os, re, json, random
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN","")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY","")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN","cskh_verify_123")

# --- Sản phẩm KKEY / CSKH ---
PRODUCTS = [
    {"name":"Áo Polo Horse","price":370000,"old":529000,"type":"ao"},
    {"name":"Áo Polo Falcon Basic","price":350000,"old":500000,"type":"ao"},
    {"name":"Quần Tây Smart Trousers Nâu","price":480000,"old":685000,"type":"quan"},
    {"name":"Giày Nam Luxury KKEY","price":650000,"old":890000,"type":"giay"},
]

# Lưu hội thoại theo từng khách, không quên nữa
sessions = {}

def get_session(uid):
    if uid not in sessions:
        sessions[uid] = {"history":[],"height":None,"weight":None,"stage":"chao","cart":[]}
    return sessions[uid]

def get_size(height, weight):
    try:
        h=int(height); w=int(weight)
    except: return "L"
    if h<165 and w<60: return "M"
    if h<172 and w<72: return "L"
    if h<178 and w<80: return "L"
    return "XL"

def call_gemini(messages, sess):
    if not GEMINI_API_KEY or not GEMINI_API_KEY.startswith("AIza"):
        return None
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        # Đưa cả lịch sử để Gemini nhớ, không hỏi lại
        history_text = "\n".join(messages[-8:])
        prompt = f"""Bạn là nhân viên tư vấn shop thời trang CSKH / KKEY, nói chuyện như em gái bán hàng, ngắn gọn, có dấu, thân thiện.
QUAN TRỌNG: Đừng bao giờ hỏi lại thông tin khách đã nói. Nếu khách đã nói chiều cao cân nặng thì dùng luôn để tư vấn size, không hỏi lại.
Nếu khách đã nói muốn mua áo + quần thì tư vấn cả 2, không hỏi lại "muốn mua áo hay quần".
Thông tin khách đã biết: cao={sess.get('height')} nặng={sess.get('weight')} giai đoạn={sess.get('stage')}
Sản phẩm: Áo Polo Horse 370k (gốc 529k), Polo Falcon Basic 350k, Quần Tây Smart Trousers 480k, Giày Nam Luxury 650k. Mua 1 miễn ship, mua 2 tặng khẩu trang UV, mua 3 tặng quần boxer.
Lịch sử chat:
{history_text}
Hãy trả lời tin nhắn cuối cùng 1 cách thông minh, đi tiếp, không lặp lại câu hỏi cũ."""
        r = requests.post(url, json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=20)
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("Gemini error:", e)
        return None

def smart_fallback(text, sess):
    low = text.lower()
    # 1. Lấy chiều cao cân nặng - NẾU ĐÃ CÓ THÌ KHÔNG HỎI LẠI
    m = re.search(r"(\d{3})\s*cm.*?(\d{2,3})\s*(cân|kg)?", low)
    if not m:
        m2 = re.search(r"cao\s*(\d{3}).*?(\d{2,3})", low)
        if m2: m=m2
    if m:
        sess["height"]=m.group(1); sess["weight"]=m.group(2)
        size = get_size(m.group(1), m.group(2))
        sess["stage"]="da_co_size"
        return f"Dạ em nhớ rồi ạ! Anh cao {m.group(1)}cm nặng {m.group(2)} cân thì mặc size {size} là đẹp nhất ạ, vừa người không bị chật.\n\nAnh thích áo Polo Horse 370k hay Polo Falcon Basic 350k ạ? Em tư vấn màu cho anh luôn. Anh thích màu trắng, đen hay xanh ạ?"
    # 2. Nếu đã có size rồi mà khách hỏi tiếp -> không hỏi lại chiều cao
    if sess.get("height") and ("áo" in low or "quần" in low or "mua" in low or "sản phẩm" in low or "có gì" in low):
        size = get_size(sess["height"], sess["weight"])
        return f"Dạ anh cao {sess['height']}cm nặng {sess['weight']} cân thì mặc size {size} ạ.\n\nShop em đang có:\n- Áo Polo Horse 370k (gốc 529k, giảm 30%)\n- Quần Tây Smart Trousers 480k\n- Giày Nam Luxury 650k\nMua 1 miễn ship, mua 2 tặng khẩu trang UV ạ.\n\nAnh lấy áo hay quần trước ạ? Em giữ size {size} cho anh nhé."
    # 3. Khách nói mua cả áo cả quần -> tư vấn combo, không hỏi lại
    if "cả áo cả quần" in low or "cả 2" in low or "mua cả" in low:
        size = get_size(sess.get("height") or 170, sess.get("weight") or 70)
        sess["stage"]="combo"
        return f"Dạ ok anh! Mua cả áo cả quần là đẹp nhất, đi thành set luôn ạ.\n\nEm gợi ý cho anh:\n- Áo Polo Horse trắng 370k size {size}\n- Quần Tây Smart Trousers nâu 480k size 31\nTổng 2 món là 850k, được miễn ship + tặng khẩu trang UV ạ.\n\nAnh chốt set này không ạ? Cho em xin SĐT + địa chỉ để em lên đơn ạ."
    # 4. Hỏi sản phẩm
    if "sản phẩm" in low or "có gì" in low or "có những gì" in low:
        return "Dạ shop em có:\n- Áo Polo Horse 370k, Polo Falcon Basic 350k\n- Quần Tây Smart Trousers 480k\n- Giày Nam Luxury 650k\nMua 1 miễn ship ạ.\n\nAnh cao bao nhiêu, nặng bao nhiêu để em tư vấn size chuẩn cho anh ạ? Anh chỉ cần nhắn 1 lần thôi, em nhớ luôn ạ."
    # 5. Khách nói "trả lời rồi mà" / bực -> xin lỗi + đi tiếp
    if "trả lời rồi" in low or "hỏi hoài" in low or "nói rồi" in low:
        if sess.get("height"):
            size = get_size(sess["height"], sess["weight"])
            return f"Dạ em xin lỗi anh, em nhớ rồi ạ, anh cao {sess['height']}cm nặng {sess['weight']} cân, size {size} ạ. Em không hỏi lại nữa đâu ạ.\n\nĐể em tư vấn luôn: Anh lấy Polo Horse 370k size {size} nhé, màu trắng dễ phối nhất ạ. Anh ok không ạ?"
        return "Dạ em xin lỗi anh, em lỡ hỏi lại. Anh cho em xin lại 1 lần thôi: Anh cao bao nhiêu, nặng bao nhiêu ạ? Em ghi nhớ luôn, không hỏi lại nữa ạ."
    # Mặc định: hỏi 1 lần duy nhất
    if sess.get("stage")=="chao":
        sess["stage"]="hoi_size"
        return "Dạ em chào anh ạ! Shop KKEY - Giày Nam Luxury đây ạ.\n\nAnh muốn mua áo, quần hay giày ạ? Anh cho em xin chiều cao + cân nặng để em tư vấn size chuẩn luôn ạ, ví dụ: Anh cao 170cm nặng 76 cân."
    return "Dạ anh muốn mua áo hay quần ạ? Anh cho em xin chiều cao + cân nặng để em tư vấn size cho chuẩn ạ."

@app.route("/", methods=["GET"])
def home():
    return "HAFOS Bot is running - Ban thong minh moi"

@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode"); token = request.args.get("hub.verify_token"); challenge = request.args.get("hub.challenge")
    if mode=="subscribe" and token==VERIFY_TOKEN:
        return challenge, 200
    return "Token sai", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if data.get("object")=="page":
        for entry in data.get("entry",[]):
            for ev in entry.get("messaging",[]):
                uid = ev["sender"]["id"]
                if "message" in ev and "text" in ev["message"]:
                    text = ev["message"]["text"]
                    sess = get_session(uid)
                    sess["history"].append(f"Khách: {text}")
                    reply = call_gemini(sess["history"], sess)
                    if not reply:
                        reply = smart_fallback(text, sess)
                    sess["history"].append(f"Bot: {reply}")
                    # Giữ lịch sử ngắn
                    sess["history"] = sess["history"][-12:]
                    send_message(uid, reply)
    return "ok", 200

def send_message(uid, text):
    if not PAGE_ACCESS_TOKEN: return
    try:
        requests.post("https://graph.facebook.com/v18.0/me/messages", params={"access_token":PAGE_ACCESS_TOKEN}, json={"recipient":{"id":uid},"message":{"text":text}}, timeout=15)
    except Exception as e:
        print(e)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
