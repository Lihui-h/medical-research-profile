# main_dashboard.py
import os
import json
import streamlit as st
from pymongo import MongoClient
import pandas as pd
from urllib.parse import urlparse
from wordcloud import WordCloud
from trycourier import Courier
from streamlit_login_auth_ui_zh.widgets import __login__
from src.dashboard.core import DataDashboard
from src.dashboard.visualizations import plot_sentiment_trend, draw_network_graph

# ==================== Courier配置 ====================
client = Courier(auth_token=st.secrets.courier.auth_token)

def send_verification_email(email, username):
    """发送机构注册验证邮件"""
    try:
        response = client.send_message(
            message={
                "to": {"email": email},
                "template": st.secrets.courier.template_id,
                "data": {
                    "recipientName": username,
                    "hospitalName": "浙江省中医院",  # 根据模板变量调整
                    "loginLink": "http://your-domain.com/login"
                }
            }
        )
        return response['requestId']
    except Exception as e:
        st.error(f"邮件发送失败: {str(e)}")
        return None

# ==================== 登录系统配置 ====================
def init_login():
    """初始化登录系统"""
    return __login__(
        auth_token=st.secrets.courier.auth_token,  # 使用Courier Token
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

def validate_referral():
    """验证跳转来源"""
    allowed_referrers = [
        "lihui-h.github.io",
        "localhost:8501",
        "medical-research-profile.streamlit.app"
    ]

    query_params = st.query_params
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
    
    try:
        login_ui = init_login()
        # 构建登录界面(添加跳转参数)
        user_logged_in = login_ui.build_login_ui()
    except Exception as e:
        st.error(f"登录系统初始化失败: {e}")
        st.stop()
    
    # 检查用户是否登录
    if user_logged_in:
        st.write(f"欢迎：{st.session_state['username']}")  # 示例
        main_dashboard()
    else:
        st.warning("认证失败，请检查账号密码")
        st.stop()