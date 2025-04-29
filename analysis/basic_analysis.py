# src/analysis/basic_analysis.py
import os
import pandas as pd
from collections import Counter
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

# ---------------------------
# 原有功能模块（保留不变）
# ---------------------------
def analyze_feedback(df):
    """基础情感分析（基于关键词）"""
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

def analyze_trend(df):
    """情感趋势分析（原有逻辑）"""
    df['period'] = pd.to_datetime(df['anonymized_date']).dt.to_period(
        "M" if os.getenv("TIME_ANONYMIZE_LEVEL") == "1" else "D"
    )
    return df.groupby('period')['sentiment'].mean()

# ---------------------------
# 新增时间线分析模块 
# ---------------------------
def build_timeline(month_window=3, collection_name="tieba_posts"):
    """
    构建就医体验时间线（新增功能）
    
    参数:
        month_window: 分析最近N个月的数据，默认3个月
        collection_name: MongoDB集合名称，默认tieba_posts
    """
    try:
        load_dotenv()
        client = MongoClient(os.getenv("MONGODB_URI"))
        db = client[os.getenv("SOCIAL_DB", "social_data")]
        
        # 从MongoDB加载数据（优化查询）
        query = {
            "post_time": {
                "$gte": datetime.now().replace(day=1) - pd.DateOffset(months=month_window)
            }
        }
        data = list(db[collection_name].find(
            query,
            {"_id": 0, "post_time": 1, "hospital": 1, "content": 1}
        ))
        
        if not data:
            print("⚠️ 未找到符合时间范围的数据")
            return None

        # 数据预处理
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(
            df['post_time'].str.extract(r'(\d{4}-\d{2}-\d{2})', expand=False),
            errors='coerce'
        )
        df = df.dropna(subset=['date'])
        
        # 生成时间线（按周聚合）
        timeline = df.groupby([
            pd.Grouper(key='date', freq='W-MON'),  # 按周起始为周一
            'hospital'
        ]).size().unstack(fill_value=0)
        
        # 保存分析结果到新集合
        db["timeline_analysis"].update_one(
            {"period": f"last_{month_window}_months"},
            {"$set": {"data": timeline.to_dict()}},
            upsert=True
        )
        
        print(f"✅ 成功生成最近{month_window}个月时间线")
        return timeline
        
    except Exception as e:
        print(f"❌ 时间线分析失败: {str(e)}")
        return None

# ---------------------------
# 命令行测试接口（兼容原有功能）
# ---------------------------
if __name__ == "__main__":
    # 测试原有情感分析
    test_df = pd.DataFrame({
        'content': ['服务满意', '效率差', '专业水平高'],
        'anonymized_date': ['2024-04-01', '2024-04-15', '2024-05-01']
    })
    print("情感分析测试:", analyze_feedback(test_df))
    
    # 测试时间线分析（需连接真实数据库）
    # build_timeline(month_window=3)