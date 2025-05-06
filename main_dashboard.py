# main_dashboard.py
import os
import json
import streamlit as st
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import pandas as pd
from wordcloud import WordCloud
from src.dashboard.core import DataDashboard
from src.dashboard.visualizations import (
    plot_sentiment_trend,
    draw_network_graph
)

# ==================== Flask API 服务配置 ====================
flask_app = Flask(__name__)
CORS(
    flask_app, resources={
        r"/api/*": {
            "origins": "https://lihui-h.github.io",  # 允许的前端域名
            "methods": ["GET", "POST", "OPTIONS"],  # 允许的方法
            "allow_headers": ["Content-Type", "Authorization"],  # 允许的头部
        }
    }
)

@flask_app.route('/api/login', methods=['POST', 'OPTIONS'])
def handle_login():
    """处理登录请求"""
    if request.method == 'OPTIONS':
        return jsonify({
            'status': 'preflight'
        }), 200
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        # 从 Streamlit Secrets 获取凭证
        valid_user = st.secrets.get("HOSPITAL_USER", "zjszyy")
        valid_pass = st.secrets.get("HOSPITAL_PASS", "Contagio@2024")

        if username == valid_user and password == valid_pass:
            return jsonify({
                "success": True,
                "redirect": "/dashboard"  # Streamlit 路由
            })
        else:
            return jsonify({
                "success": False,
                "error": "机构代码或安全密钥错误"
            }), 401

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"服务器错误: {str(e)}"
        }), 500

# ==================== Streamlit 仪表盘配置 ====================
def get_font_path():
    """获取中文字体路径"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for ext in [".ttf", ".otf"]:
        path = os.path.join(base_dir, "assets", "fonts", f"SmileySans-Oblique{ext}")
        if os.path.exists(path):
            return path
    return None

def main_dashboard():
    """主仪表盘界面"""
    st.set_page_config(
        page_title="ContagioScope 数据驾驶舱",
        page_icon="🔬",
        layout="wide"
    )
    
    # 初始化数据驾驶舱
    dashboard = DataDashboard(st.secrets["MONGODB_URI"])
    
    st.title("🛸 ContagioScope 数据驾驶舱")
    
    # 数据加载
    with st.spinner("🚀 正在加载数据..."):
        df = dashboard.load_hospital_data(limit=200)
    
    # 核心指标看板
    col1, col2, col3 = st.columns(3)
    col1.metric("总讨论帖数", len(df))
    col2.metric("涉及医院数", df["hospital"].nunique())
    col3.metric("最新数据时间", df["date"].max())
    
    # 可视化分页
    tab1, tab2 = st.tabs(["趋势分析", "传播网络"])
    with tab1:
        fig = plot_sentiment_trend(df)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        html_path = draw_network_graph(df)
        if os.path.exists(html_path):
            st.components.v1.html(open(html_path).read(), height=600)
        else:
            st.error("网络图生成失败")
    
    # 医院词云
    if font_path := get_font_path():
        hospital_text = " ".join(df["hospital"].tolist())
        wordcloud = WordCloud(
            font_path=font_path,
            width=800,
            height=400,
            background_color="#1a1a1a",
            colormap="YlGnBu"
        ).generate(hospital_text)
        st.image(wordcloud.to_array(), caption="医院提及频率词云")

# ==================== 集成 Flask 和 Streamlit ====================
if __name__ == '__main__':
    import streamlit.runtime.scriptrunner as scriptrunner
    
    # 挂载 Flask 到 Streamlit 服务器
    from streamlit.web.server import Server
    server = Server.get_current()
    server._flask_app.wsgi_app = flask_app.wsgi_app
    
    # 设置 Streamlit 路由
    @flask_app.route('/ContagioScope_DataDashboard')
    def streamlit_route():
        """处理仪表盘路由"""
        scriptrunner.run_script(__file__, "", [])
        return ""
    
    # 启动服务
    if os.environ.get("STREAMLIT_SERVER_PORT"):
        # 生产环境
        server.start()
    else:
        # 本地开发
        flask_app.run(port=8501)
