from collections import defaultdict
import jieba.analyse
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

class DoctorEvaluator:
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGODB_URI"))
        self.db = self.client[os.getenv("SOCIAL_DB", "social_data")]
        self.collection = self.db["tieba_posts"]
        
        # 医生名单（与关键词一致）
        self.doctors = ["何强", "高祥福", "张弘", "施翔", 
                       "林胜友", "黄抒伟", "钱宇", "夏永良", "周秀扣"]

    def build_matrix(self):
        """生成医生-关键词矩阵"""
        matrix = defaultdict(list)
        
        # 从MongoDB读取数据
        posts = self.collection.find(
            {"content": {"$regex": "|".join(self.doctors)}}
        )
        
        for post in posts:
            content = post["content"]
            for doctor in self.doctors:
                if doctor in content:
                    # 提取关键词（TF-IDF算法）
                    keywords = jieba.analyse.extract_tags(
                        content, 
                        topK=5, 
                        allowPOS=('n', 'vn', 'v')
                    )
                    matrix[doctor].extend(keywords)
        
        # 保存到新集合
        self.db["doctor_keywords"].insert_one({
            "timestamp": datetime.now(),
            "matrix": dict(matrix)
        })
        print("医生评价矩阵已更新")

# 命令行调用
if __name__ == "__main__":
    evaluator = DoctorEvaluator()
    evaluator.build_matrix()