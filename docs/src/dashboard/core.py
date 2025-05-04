# src/dashboard/core.py
import os
import re
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
from src.utils.anonymizer import anonymize_text

class DataDashboard:
    """数据驾驶舱核心类（增强版）"""
    
    def __init__(self, mongo_uri: str = None):
        """支持外部注入MongoDB连接"""
        load_dotenv()  # 加载环境变量
        
        # 优先级：参数传入 > 环境变量 > 默认值
        self.mongo_uri = mongo_uri or os.getenv("MONGODB_URI")
        self.db_name = os.getenv("MONGODB_DB", "social_data")
        
        if not self.mongo_uri:
            raise ValueError("MongoDB URI未配置！")
            
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.db_name]

    def load_hospital_data(self, limit: int = 100) -> pd.DataFrame:
        """从贴吧帖子中提取医院信息（增强版）"""
        try:
            collection = self.db["tieba_posts"]
            
            # 优化查询语句
            projection = {
                "_id": 0,
                "content": 1,
                "post_time": 1,
                "author": 1,
                "detail_url": 1
            }
            
            data = list(collection.find(
                filter={"content": {"$exists": True}},
                projection=projection
            ).limit(limit))

            # === 新增：医院名称提取优化 ===
            hospital_pattern = re.compile(
                r"([\u4e00-\u9fa5]{2,}(?:大学)?[附属]?[市第]?[中西医结合]?[医院|卫生院|诊疗中心])",
                flags=re.IGNORECASE
            )
            
            df = pd.DataFrame(data)
            df["hospital"] = df["content"].apply(
                lambda x: self._extract_hospital(x, hospital_pattern)
            )
            
            # 时间处理增强
            df["date"] = pd.to_datetime(
                df["post_time"], 
                errors='coerce'
            ).dt.strftime("%Y-%m-%d")
            
            return df.dropna(subset=["hospital"])

        except Exception as e:
            print(f"数据加载失败: {str(e)}")
            return pd.DataFrame()

    def _extract_hospital(self, text: str, pattern: re.Pattern) -> str:
        """医院名称提取工具方法"""
        matches = pattern.findall(text)
        if matches:
            # 优先返回最长匹配项
            return max(matches, key=len)
        return "未知机构"

    def generate_summary(self, df: pd.DataFrame) -> dict:
        """生成增强版统计摘要"""
        try:
            # 新增科室关键词分析
            dept_keywords = ["内科", "外科", "急诊", "妇产科", "儿科"]
            content_str = " ".join(df["content"].tolist())
            
            return {
                "total_reviews": len(df),
                "top_hospitals": df["hospital"].value_counts().head(5).to_dict(),
                "department_dist": {
                    k: content_str.count(k) 
                    for k in dept_keywords
                }
            }
            
        except KeyError:
            return {"error": "数据字段缺失"}