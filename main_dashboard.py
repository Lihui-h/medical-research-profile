# main_dashboard.py
import streamlit as st
import hashlib
import time
import sys
import json
from pymongo import MongoClient
import pandas as pd
from src.dashboard.core import DataDashboard
from src.dashboard.visualizations import plot_sentiment_trend

# ==================== 页面配置（必须最前） ====================
st.set_page_config(
        page_title="ContagioScope 数据驾驶舱",
        page_icon="🔬",
        layout="wide"
)

# ==================== 安全验证模块 ====================
def generate_hash(input_str: str) -> str:
    """生成 SHA-256 哈希值"""
    return hashlib.sha256(input_str.encode()).hexdigest()

def validate_credentials(username: str, password: str) -> bool:
    """验证用户名密码（哈希比对）"""
    valid_user_hash = st.secrets.get("HOSPITAL_USER_HASH", "")
    valid_pass_hash = st.secrets.get("HOSPITAL_PASS_HASH", "")
    return (
        generate_hash(username) == valid_user_hash
        and generate_hash(password) == valid_pass_hash
    )

# ==================== API 处理模块 ====================
def handle_request():
    """处理外部 API 请求"""
    params = st.query_params

    # 仅处理 /api/login 路径的请求
    if params.get("path") == ["/api/login"]:
        # ==== 获取参数 ====
        username = params.get("username", [""])[0]
        password = params.get("password", [""])[0]

        # ==== 构造响应 ====
        response_data = {}
        if validate_credentials(username, password):
            response_data = {
                "success": True,
                "token": generate_hash(f"{username}{password}{int(time.time())}"),
                "redirect": st.secrets.get("REDIRECT_URL", "/")
            }
            status_code = 200
        else:
            response_data = {
                "success": False,
                "error": "认证失败"
            }
            status_code = 401

        # 直接返回原始 HTTP 响应
        from flask import Response
        return Response(
            json.dumps(response_data),
            status=status_code,
            mimetype="application/json",
            headers={
                "Access-Control-Allow-Origin": "https://lihui-h.github.io",
                "Access-Control-Allow-Methods": "GET, POST"
            }
        )
        
    # 正常渲染页面
    return None

# ==================== 数据看板模块 ====================
def show_dashboard():
    """显示数据看板"""
    # 初始化数据连接
    dashboard = DataDashboard(st.secrets["MONGODB_URI"])
    
    # 实时数据加载
    with st.spinner("🚀 正在加载数据..."):
        df = dashboard.load_hospital_data(limit=500)
    
    # 核心指标看板
    col1, col2, col3 = st.columns(3)
    col1.metric("总讨论帖数", len(df))
    col2.metric("涉及医院数", df["hospital"].nunique())
    col3.metric("最新数据时间", df["date"].max())
    
    # 可视化展示
    tab1, tab2 = st.tabs(["趋势分析", "传播网络"])
    with tab1:
        fig = plot_sentiment_trend(df)
        st.plotly_chart(fig, use_container_width=True)
    
    # 更多可视化组件...

# ==================== 主流程控制 ====================
if __name__ == "__main__":
    # 处理 API 请求
    response = handle_request()
    if response:
        # 绕过 Streamlit 中间件直接返回响应
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        _get_websocket_headers()._headers = response.headers
        st.write(response.get_data())
        st.stop()
    else:
        # 会话状态初始化
        if "logged_in" not in st.session_state:
            st.session_state.logged_in = False
    
        # 登录状态检查
        if not st.session_state.logged_in:
            st.title("机构认证")
        
            with st.form("login_form"):
                username = st.text_input("机构代码", key="username")
                password = st.text_input("安全密钥", type="password", key="password")
                submitted = st.form_submit_button("授权登录")
            
                if submitted:
                    if validate_credentials(username, password):
                        st.session_state.logged_in = True
                        st.rerun()
                    else:
                        st.error("⚠️ 认证失败：请检查机构代码和安全密钥")
        else:
            show_dashboard()