# 在项目根目录创建 build_static.py
import json
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
data = list(client.medical_db.hospitals.find({}, {'_id': 0}))

with open('docs/data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)