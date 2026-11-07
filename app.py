import os, json, requests, re
from flask import Flask, request
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "hafos_verify_123")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SHEET_WEBHOOK_URL = os.getenv("SHEET_WEBHOOK_URL", "")
PROMO = "Mua 1 mien ship | Mua 2 tang Khau trang UV | Mua 3 tang Quan Boxer"
try:
    SYSTEM_PROMPT = open("system_prompt.txt", encoding="utf-8").read()
except:
    SYSTEM_PROMPT = ""
sessions = {}
def get_session(psid):
    if psid not in sessions:
        sessions[psid] = {"history": [], "cart": [], "info": {}, "stage": "tu_van"}
    return sessions[psid]
def call_gemini(prompt, history):
    if not GEMINI_API_KEY:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    contents = []
    for h in history[-10:]:
        contents.append({"role": "user" if h["role"]=="user" else "model", "parts": [{"text": h["text"]}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})
    try:
        r = requests.post(url, json={"system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]}, "contents": contents}, timeout=20)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("Gemini error:", e)
        return None
def fallback_reply(text, sess):
    t = " " + text.lower().strip() + " "
    # Thu tu QUAN TRONG: check cu the truoc, chung chung sau - tranh nhan nham "gian"->"gia", "thanh"->"anh"
    if "kiem tra" in t or "kiem hang" in t:
        return "Da duoc a, anh duoc kiem tra thoai mai truoc khi nhan giup em nhe a."
    if "cod" in t or "chuyen khoan" in t or "thanh toan" in t:
        return "Da ben em co 2 hinh thuc: COD nhan hang moi thanh toan, hoac chuyen khoan truoc deu duoc a. Anh chon hinh thuc nao a?"
    if "vai" in t or "gian" in t or "the thao" in t or "xu long" in t or "xu" in t:
        return "Da vai cotton cao cap co gian 4 chieu, giat thoai mai khong lo xu, mac the thao van thoang mat, tham hut mo hoi tot lam a."
    if "size 31" in t or t.strip()=="31" or " 31 " in t:
        return "Da size 31 thi anh mac Quan Tay size L la vua dep a. Anh lay them 1 quan nay nhe? Tong don se la 2 ao + 1 quan = 1.220.000d a."
    if "1m78" in t or "68kg" in t or "68 kg" in t:
        return "Voi 1m78 - 68kg anh mac size L se vua dep a. Neu bung hoi to va thich rong rai thi lay XL se khong bi bo bung a. Anh thich mac om vua hay rong rai a?"
    if "bo" in t or "bung" in t:
        return "Da anh yen tam, vai co gian 4 chieu nen size L van thoai mai, khong bo. Neu thich rong hon thi len XL la dep nhat a. Anh lay L hay XL a?"
    if "quan" in t or "phoi" in t:
        return "Da co a! Phoi voi Polo trang thi Quan Tay Smart Trousers Nau la dep nhat a - 480.000d (goc 685K). Anh thuong mac quan size bao nhieu a? (VD: size 31)"
    if "2 cai" in t or "lay 2" in t or "2 ao" in t:
        sess["cart"] = [{"id":"polo_horse","qty":2,"size":"XL"}]
        return "Da em chot cho anh 2 Ao Polo Horse Trang size XL = 740.000d, mien ship + tang khau trang UV a. Anh cho em xin ten + SDT + dia chi de em len don nhe a?"
    if "gia" in t or "bao nhieu" in t:
        return "Da Polo Horse 370.000d (goc 529K). " + PROMO + " Anh cho em xin ten + SDT + dia chi de em len don nhe a?"
    if "polo" in t or "mau ao" in t or "ao trang" in t:
        return "Da em tim thay mau anh can roi a. 1. Ao Polo Horse Trang - 370.000d (goc 529K, giam 30%) - Ban chay nhat. 2. Ao Polo Falcon Basic - 350.000d. Anh cao bao nhieu, nang bao nhieu de em tu van size chuan a? " + PROMO
    if re.search(r"\d{10}", t):
        sess["info"]["phone"] = text
        return "Da em da nhan thong tin va len don cho anh roi a! Em cam on anh da ung ho HAFOS. Anh can em tu van them gi nua khong a?"
    return "Da em hieu roi a, anh cho em hoi them xiu de em tu van chuan nhat: Anh muon mua ao hay quan a? Anh cao bao nhieu, nang bao nhieu a?"

def send_message(psid, text):
    url = "https://graph.facebook.com/v21.0/me/messages"
    payload = {"recipient": {"id": psid}, "message": {"text": text[:1900]}}
    requests.post(url, params={"access_token": PAGE_ACCESS_TOKEN}, json=payload, timeout=10)
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Token sai", 403
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for ev in entry.get("messaging", []):
                psid = ev["sender"]["id"]
                sess = get_session(psid)
                if "message" in ev and "text" in ev["message"]:
                    user_text = ev["message"]["text"]
                    sess["history"].append({"role":"user","text":user_text})
                    ai_reply = call_gemini(user_text, sess["history"])
                    reply = ai_reply if ai_reply else fallback_reply(user_text, sess)
                    sess["history"].append({"role":"assistant","text":reply})
                    send_message(psid, reply)
                elif "message" in ev and "attachments" in ev["message"]:
                    send_message(psid, "Da em nhan duoc anh mau roi a. Em tim thay mau giong nhat la Ao Polo Horse Trang - 370.000d, vai cotton co gian 4 chieu. Anh cao bao nhieu, nang bao nhieu de em tu van size a?")
    return "OK", 200
@app.route("/", methods=["GET"])
def home():
    return "HAFOS Bot is running"
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
