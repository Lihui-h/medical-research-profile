# main_dashboard.py
import os
import json
import streamlit as st
from pymongo import MongoClient
import pandas as pd
from urllib.parse import urlparse
from wordcloud import WordCloud
from streamlit_login_auth_ui_zh.widgets import __login__
from src.dashboard.core import DataDashboard
from src.dashboard.visualizations import plot_sentiment_trend, draw_network_graph

# ==================== 登录系统配置 ====================
def init_login():
    """初始化登录系统"""
    return __login__(
        auth_token="courier_auth_token",  # 暂时使用模拟token
        company_name="流形暗面",
        width=300,
        height=400,
        logout_button_name="退出登录",
        hide_menu_bool=True,
        hide_footer_bool=True,
        lottie_url='https://assets2.lottiefiles.com/packages/lf20_ktwnwv5m.json'
    )

# ==================== 主仪表盘 ====================
def main_dashboard():
    """主分析仪表盘"""
    st.set_page_config(
        page_title="ContagioScope 数据驾驶舱",
        page_icon="🔬",
        layout="wide"
    )
    
    # 初始化数据引擎
    dashboard = DataDashboard(os.getenv("MONGODB_URI"))
    
    st.title("🛸 ContagioScope 数据驾驶舱")
    st.markdown("### 当前用户: " + st.session_state.user_email)
    
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

# ==================== 工具函数 ====================
def get_font_path():
    """获取中文字体路径"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for ext in [".ttf", ".otf"]:
        path = os.path.join(base_dir, "assets", "fonts", f"SmileySans-Oblique{ext}")
        if os.path.exists(path):
            return path
    return None

def handle_user_registration(email, username, password):
    """处理用户注册到MongoDB"""
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client["user_management"]
    
    # 检查用户是否存在
    if db.users.find_one({"$or": [{"email": email}, {"username": username}]}):
        return False
    
    # 插入新用户
    db.users.insert_one({
        "email": email,
        "username": username,
        "password": password,  # 实际应存储哈希值
        "registration_date": pd.Timestamp.now(),
        "access_level": "basic"
    })
    return True

def validate_referral():
    """验证跳转来源"""
    allowed_referrers = [
        "lihui-h.github.io",
        "localhost:8501",
        "medical-research-profile.streamlit.app"
    ]

    query_params = st.experimental_get_query_params()
    if "page" not in query_params:
        st.markdown(f"""
        <script>
            window.location.href = "https://lihui-h.github.io/medical-research-profile/";
        </script>
        """, unsafe_allow_html=True)
        st.stop()

    if query_params.get("page")[0] == "login":
        st.session_state.login_redirect = True

# ==================== 主程序入口 ====================
if __name__ == '__main__':
    # 验证跳转来源
    validate_referral()

    # 初始化登录系统
    login_ui = init_login()
    
    # 构建登录界面(添加跳转参数)
    user_logged_in = login_ui.build_login_ui(
        preauthorized_domains=["zjsru.edu.cn", "contagioscope.ai"],
        registration_callback=handle_user_registration,
        extra_params={
            "referrer": "github_pages",
            "utm_source": "medical_research_protal"
        }
    )
    
    # 登录成功后显示主界面
    if user_logged_in:
        st.session_state.user_email = login_ui.get_email()
        main_dashboard()