# src/dashboard/core.py
import os
import re
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
from src.utils.anonymizer import anonymize_text  # 复用已有工具

class DataDashboard:
    def __init__(self):
        # 从环境变量读取，而非硬编码
        mongodb_uri = os.getenv("MONGODB_URI")
        print(f"DEBUG - MONGODB_URI: {mongodb_uri}")  # 输出到 Streamlit 日志
        if not mongodb_uri:
            raise ValueError("MONGODB_URI 未设置")
        
        try:
            self.client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')  # 主动触发连接测试
            print("DEBUG - 成功连接到 MongoDB Atlas")
        except Exception as e:
            print(f"DEBUG - 连接失败: {str(e)}")
            raise
        
        self.db = self.client["social_data"]
    
    def load_hospital_data(self, limit=100):
        """从贴吧帖子中提取医院信息"""
        collection = self.db["tieba_posts"]
        data = list(collection.find(
            {}, 
            {"_id": 0, "content": 1, "post_time": 1, "author": 1}
        ).limit(limit))

        

        # === 新增：从content提取医院名称 ===
        # 正则匹配 "XX医院" 模式
        hospital_pattern = r"([\u4e00-\u9fa5]{2,}(?:大学)?[附属]?[市第]?[中西医结合]?[医院|卫生院|诊疗中心])"
        df = pd.DataFrame(data)
        df["hospital"] = df["content"].apply(
            lambda x: re.findall(hospital_pattern, x)[0] 
            if re.search(hospital_pattern, x) 
            else "未知机构"
        )

        # 转换时间格式
        df["date"] = pd.to_datetime(df["post_time"]).dt.strftime("%Y-%m-%d")  # 将post_time映射为date
        # 清洗无效数据
        df = df[df["hospital"] != "未知机构"]
        return df
    
    def generate_summary(self, df):
        """生成基础统计摘要"""
        return {
            "total_reviews": len(df),
            "top_keywords": df["content"].str.split(expand=True).stack().value_counts().head(5).to_dict()
        }