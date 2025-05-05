# api_service.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import hashlib
import os

app = Flask(__name__)
CORS(app, origins=["https://lihui-h.github.io"])  # 严格限制来源

# 从环境变量读取凭证
VALID_USER_HASH = os.getenv("HOSPITAL_USER_HASH")
VALID_PASS_HASH = os.getenv("HOSPITAL_PASS_HASH")

@app.route('/api/login', methods=['GET'])
def login():
    username = request.args.get('username', '')
    password = request.args.get('password', '')
    
    # 哈希验证
    user_hash = hashlib.sha256(username.encode()).hexdigest()
    pass_hash = hashlib.sha256(password.encode()).hexdigest()
    
    if user_hash == VALID_USER_HASH and pass_hash == VALID_PASS_HASH:
        return jsonify({
            "success": True,
            "token": hashlib.sha256(f"{username}{password}{os.urandom(16)}".encode()).hexdigest(),
            "redirect": os.getenv("STREAMLIT_URL", "https://medical-research-profile-ke2ztwqjq7z585fuompiq4.streamlit.app")
        })
    else:
        return jsonify({"success": False, "error": "认证失败"}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)