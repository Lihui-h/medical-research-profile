# build_static.py
import os
import json
from pymongo import MongoClient

def export_data():
    try:
        # 从环境变量读取配置
        mongodb_uri = os.getenv("MONGODB_URI")
        db_name = os.getenv("MONGODB_DB", "medical_db")
        collection_name = os.getenv("MONGODB_COLLECTION", "hospitals")

        if not mongodb_uri:
            raise ValueError("MONGODB_URI 未配置！")

        # 连接 MongoDB Atlas
        client = MongoClient(mongodb_uri)
        db = client[db_name]
        collection = db[collection_name]

        # 查询数据并保存为 JSON
        data = list(collection.find({}, {'_id': 0}))
        with open('docs/data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("数据导出成功！")

    except Exception as e:
        print(f"数据导出失败: {str(e)}")
        raise

if __name__ == "__main__":
    export_data()