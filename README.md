# HAFOS AI Bot - Ban that chay voi Facebook Messenger

## 1. Lay Token (5 phut)
1. Vao https://developers.facebook.com -> Tao App -> Them san pham Messenger
2. Chon Page HAFOS
3. Messenger > Settings: Lay Page Access Token -> dan vao .env
4. Dat Verify Token = hafos_verify_123
5. Callback URL: https://domain-cua-ban/webhook + Verify Token -> Verify & Save
6. Subscribe Page: chon messages, messaging_postbacks

## 2. Lay Gemini API Key (mien phi)
- Vao https://aistudio.google.com/app/apikey -> Create API Key -> dan vao .env
- Neu khong co key, bot van chay bang Fallback Rule (khong can AI van chot don nhu video)

## 3. Chay local de test
pip install -r requirements.txt
cp .env.example .env (roi dien token that)
python app.py
ngrok http 5000

## 4. Deploy len Render (mien phi, chay 24/7)
- Push code len GitHub -> render.com -> New Web Service
- Build: pip install -r requirements.txt
- Start: gunicorn app:app
- Them Environment Variables tu .env vao Render

## 5. Test nhanh
Nhan cho Page: "Gui anh mau ao", "Minh cao 1m78 nang 68kg", "Bung hoi to co bi bo khong", "Co quan phoi khong", "Lay 2 cai"
Bot phai tra loi dung nhu video: 2 ao + 1 quan = 1.220.000d
