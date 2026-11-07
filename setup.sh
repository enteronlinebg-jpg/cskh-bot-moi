#!/bin/bash
# Chay 1 lenh la xong
pip install -r requirements.txt
cp .env.example .env 2>/dev/null || true
echo '--- Dien Token vao file .env roi chay: python app.py ---'
cat .env.example
