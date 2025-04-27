# main_dashboard.py
import os
import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import ImageFont
from wordcloud import WordCloud
from src.dashboard.core import DataDashboard
from src.dashboard.visualizations import (
    plot_sentiment_trend,
    draw_network_graph
)

# 配置页面
st.set_page_config(
    page_title="ContagioScope 数据驾驶舱",
    page_icon="🔬",
    layout="wide"
)

def get_font_path():
    """优先尝试TTF，失败后尝试OTF"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_paths = [
        os.path.join(base_dir, "assets", "fonts", "SmileySans-Oblique.ttf"),
        os.path.join(base_dir, "assets", "fonts", "SmileySans-Oblique.otf")
    ]
    for path in font_paths:
        if os.path.exists(path):
            return path
    return None


def main():
    # 初始化驾驶舱
    st.title("🛸 ContagioScope 数据驾驶舱")
    dashboard = DataDashboard()
    
    # === 数据加载 ===
    with st.spinner("🚀 正在加载数据..."):
        df = dashboard.load_hospital_data()
    
    # === 核心指标看板 ===
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总讨论帖数", len(df))
    with col2:
        st.metric("涉及医院数", df["hospital"].nunique())  # 使用新字段
    with col3:
        latest_date = df["post_time"].max()  # 使用实际存在的post_time字段
        st.metric("最新数据时间", latest_date)
    
    # === 可视化展示 ===
    tab1, tab2 = st.tabs(["趋势分析", "传播网络"])
    
    with tab1:
        fig = plot_sentiment_trend(df)
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        html_path = draw_network_graph(df)
        if os.path.exists(html_path):
            st.components.v1.html(open(html_path).read(), height=600)
        else:
            st.error(f"网络图文件未生成，预期路径：{html_path}")
    
    # === 新增：医院词云 ===
    font_path = get_font_path()
    if not font_path:
        st.error("⚠️ 字体文件未找到，请检查assets/fonts目录")
        return

    # 指定字体路径
    hospital_text = " ".join(df["hospital"].tolist())
    
    # 生成词云（带中文字体）
    wordcloud = WordCloud(
        font_path=font_path,        # 关键参数
        width=800, height=400, 
        background_color="#1a1a1a",  # 暗色背景
        colormap="YlGnBu"
    ).generate(hospital_text)

    st.image(wordcloud.to_array(), caption="医院提及频率词云")

if __name__ == "__main__":
    main()