# main_dashboard.py
import streamlit as st
import hashlib
import time
import json
from pymongo import MongoClient
import pandas as pd
from flask import Flask, request, Response
from flask_cors import CORS
from src.dashboard.core import DataDashboard
from src.dashboard.visualizations import plot_sentiment_trend

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
def handle_api_request():
    """处理外部 API 请求"""
    params = st.experimental_get_query_params()
    
    if params.get("api") == ["login"]:
        # 强制设置CORS头
        from flask import Response
        headers = {
            "Access-Control-Allow-Origin": "https://lihui-h.github.io",
            "Access-Control-Allow-Methods": "GET, POST",
            "Access-Control-Allow-Headers": "Content-Type"
        }

        # 从 URL 参数获取凭证
        username = params.get("username", [""])[0]
        password = params.get("password", [""])[0]
        
        # 返回 JSON 响应
        if validate_credentials(username, password):
            response_data = {
                "success": True,
                "token": generate_hash(f"{username}{password}{int(time.time())}"),
                "redirect": st.secrets.get("DASHBOARD_URL", "/")
            }
            return Response(
                json.dumps(response_data),
                headers=headers,
                mimetype="application/json"
            )
        else:
            response_data = {"success": False, "error": "认证失败"}
            return Response(
                json.dumps(response_data),
                headers=headers,
                mimetype="application/json",
                status=401
            )
        
        # 终止 Streamlit 后续渲染
        st.stop() 

# ==================== 数据看板模块 ====================
def show_dashboard():
    """显示数据看板"""
    st.set_page_config(
        page_title="ContagioScope 数据驾驶舱",
        page_icon="🔬",
        layout="wide"
    )
    
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
    # 优先处理 API 请求
    handle_api_request()
    
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