#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "flask>=3.1.2",
#     "requests>=2.32.5",
# ]
# ///

# -*- coding: utf-8 -*-

"""
Z.AI API Proxy for Xcode
localhost:8080/v1/* -> https://api.z.ai/api/coding/paas/v4/*
"""

from flask import Flask, request, Response
import requests
import os

app = Flask(__name__)

ZAI_API_KEY = os.getenv("ZAI_API_KEY", "YOUR_API_KEY_HERE")
TARGET_BASE_URL = "https://api.z.ai/api/coding/paas/v4"

@app.route('/v1/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def proxy(path):
    # 転送先のURL
    target_url = f"{TARGET_BASE_URL}/{path}"
    
    # リクエストヘッダーをコピー (Host以外)
    headers = {key: value for key, value in request.headers if key.lower() != 'host'}
    
    # Authorizationヘッダーがあればそれをそのまま使用、なければAPI Keyを設定
    if 'Authorization' not in headers:
        headers['Authorization'] = f'Bearer {ZAI_API_KEY}'
    
    # クエリパラメータ
    params = request.args
    
    # リクエストボディ
    data = request.get_data()
    
    print(f"[PROXY] {request.method} {target_url}")
    print(f"[HEADERS] {headers}")
    
    # リクエストを転送
    try:
        response = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=params,
            data=data,
            stream=True,
            allow_redirects=False
        )
        
        # レスポンスヘッダーをコピー
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(name, value) for name, value in response.raw.headers.items()
                          if name.lower() not in excluded_headers]
        
        # レスポンスを返す
        return Response(
            response.iter_content(chunk_size=1024),
            status=response.status_code,
            headers=response_headers
        )
    except Exception as e:
        print(f"[ERROR] {e}")
        return {"error": str(e)}, 500

if __name__ == '__main__':
    print("Starting Z.AI Proxy Server...")
    print(f"Proxying localhost:8080/v1/* -> {TARGET_BASE_URL}/*")
    print(f"Using API Key: {ZAI_API_KEY[:10]}...")
    app.run(host='127.0.0.1', port=8080, debug=True)
