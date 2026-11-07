
import os, re
from flask import Flask, request, jsonify
import requests
app = Flask(__name__)
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN","")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY","")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN","cskh_verify_123")
sessions = {}
def get_session(uid):
    if uid not in sessions:
        sessions[uid] = {"history":[],"height":None,"weight":None,"stage":"chao","cart":"Polo Horse + Quan Tay"}
    return sessions[uid]
def get_size(h,w):
    try:
        h=int(h); w=int(w)
    except: return "L"
    if h<165 and w<60: return "M"
    if h<172 and w<72: return "L"
    if h<178 and w<80: return "L"
    return "XL"
def call_gemini(history, sess):
    if not GEMINI_API_KEY: return None
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        prompt = f"""Ban la nhan vien shop KKEY. Khach da biet: cao={sess.get('height')} nang={sess.get('weight')}. TUYET DOI KHONG HOI LAI chieu cao can nang, khong hoi lai 'mua ao hay quan' neu khach da chot. Neu khach noi Ok / Chot / gui SDT + dia chi thi XAC NHAN DON HANG luon, tong tien, cam on.
Lich su:\n{chr(10).join(history[-8:])}\nTra loi ngan, tieng Viet co dau."""
        r = requests.post(url, headers={"x-goog-api-key":GEMINI_API_KEY,"Content-Type":"application/json"}, json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=20)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("gemini",e); return None
def fallback(text, sess):
    low=text.lower()
    # 1. SDT + dia chi -> CHOT DON, khong hoi lai
    if re.search(r"0\d{9,10}", text) or "nguyen" in low or "duong" in low or "phuong" in low or "bac giang" in low:
        sess["stage"]="da_chot"
        return "Da em nhan don roi a! Cam on anh nhieu a.\n\nDon cua anh: Ao Polo Horse 370k + Quan Tay Smart Trousers 480k = 850k, mien ship + tang khau trang UV.\nAnh Kien - 0852789222 - So 4 duong Vuong Van Tra, phuong Tran Nguyen Han, Bac Giang.\nBen em se goi dien xac nhan va gui hang cho anh trong hom nay a. Anh cho em kiem tra hang truoc khi thanh toan a."
    if low.strip() in ["ok","ok a","ok anh","chot","chot a","chot don","lay","lay set nay","dong y"]:
        sess["stage"]="cho_dia_chi"
        return "Da anh chot set Polo Horse 370k + Quan Tay 480k = 850k, mien ship + tang khau trang UV a.\n\nAnh cho em xin SDT + dia chi de em len don cho anh a, vi du: 085... - So 4 duong..."
    # 2. Chieu cao can nang
    m=re.search(r"(\d{3})\s*cm.*?(\d{2,3})", low)
    if m:
        sess["height"]=m.group(1); sess["weight"]=m.group(2); sess["stage"]="da_co_size"
        size=get_size(m.group(1),m.group(2))
        return f"Da em nho roi a, anh cao {m.group(1)}cm nang {m.group(2)} can thi mac size {size} la dep a.\n\nEm goi y: Ao Polo Horse 370k + Quan Tay 480k = 850k, mien ship a. Anh chot set nay khong a?"
    # 3. Neu DA CO chieu cao thi KHONG BAO GIO hoi lai
    if sess.get("height"):
        size=get_size(sess["height"], sess["weight"])
        if "tra loi roi" in low or "hoi hoai" in low or "noi roi" in low:
            return f"Da em xin loi anh, em nho roi, anh cao {sess['height']}cm nang {sess['weight']} can, size {size} a. Anh chot set Polo 370k + Quan 480k = 850k khong a?"
        return f"Da anh cao {sess['height']}cm nang {sess['weight']} can, size {size} a. Anh chot set Polo Horse 370k + Quan Tay 480k = 850k, mien ship a? Anh nhan 'Chot' giup em la em len don a."
    # 4. Chua co thong tin -> hoi 1 lan
    if sess["stage"]=="chao":
        sess["stage"]="hoi_size"
        return "Da em chao anh a, shop KKEY day a. Anh muon mua ao hay quan a? Anh cho em xin chieu cao + can nang de em tu van size a, vi du: Anh cao 170cm nang 76 can."
    return "Da anh cho em xin chieu cao + can nang a, em tu van size cho anh a."
@app.route("/", methods=["GET"])
def home(): return "HAFOS Bot is running - Ban thong minh v3"
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.mode")=="subscribe" and request.args.get("hub.verify_token")==VERIFY_TOKEN:
        return request.args.get("hub.challenge"),200
    return "sai",403
@app.route("/webhook", methods=["POST"])
def webhook():
    data=request.get_json() or {}
    for entry in data.get("entry",[]):
        for ev in entry.get("messaging",[]):
            uid=ev["sender"]["id"]
            if "message" in ev and "text" in ev["message"]:
                text=ev["message"]["text"]; sess=get_session(uid)
                sess["history"].append(f"Khach: {text}")
                reply=call_gemini(sess["history"], sess)
                if not reply: reply=fallback(text, sess)
                sess["history"].append(f"Bot: {reply}"); sess["history"]=sess["history"][-12:]
                try: requests.post("https://graph.facebook.com/v18.0/me/messages", params={"access_token":PAGE_ACCESS_TOKEN}, json={"recipient":{"id":uid},"message":{"text":reply}}, timeout=15)
                except Exception as e: print(e)
    return "ok",200
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
