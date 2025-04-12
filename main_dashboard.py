# main_dashboard.py
import streamlit as st
from src.analysis.basic_analysis import analyze_feedback, get_top_keywords

st.title("医疗质量基础分析看板")

# 数据加载
df = analyze_feedback("data/processed/cleaned_data.csv")

# 指标展示
col1, col2 = st.columns(2)
with col1:
    st.metric("正面评价比例", 
             f"{len(df[df['sentiment']=='positive'])/len(df):.1%}")
with col2:
    st.metric("高频投诉关键词", 
             get_top_keywords(df[df['sentiment']=='negative'])[0][0])

# 原始数据预览
st.write("### 原始数据示例", df.sample(3))