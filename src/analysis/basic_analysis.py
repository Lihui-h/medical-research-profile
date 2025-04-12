# src/analysis/basic_analysis.py
import pandas as pd
from collections import Counter

def analyze_feedback(file_path):
    """基础情感分析（基于关键词）"""
    df = pd.read_csv(file_path)
    
    # 情感词库（需扩展）
    positive_words = ['满意', '专业', '及时']
    negative_words = ['差', '投诉', '拖延']
    
    df['sentiment'] = df['content'].apply(
        lambda x: 'positive' if any(w in x for w in positive_words) 
        else 'negative' if any(w in x for w in negative_words) 
        else 'neutral'
    )
    
    return df

def get_top_keywords(df, n=10):
    """提取高频关键词"""
    words = ' '.join(df['content']).split()
    return Counter(words).most_common(n)