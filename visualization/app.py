from flask import Flask, render_template
from pymongo import MongoClient
import pandas as pd
import plotly.express as px

app = Flask(__name__)

# MongoDB连接
client = MongoClient("mongodb://localhost:27017/")
db = client["medical_db"]
collection = db["hospitals"]

@app.route('/')
def dashboard():
    # 获取全部数据
    data = list(collection.find())
    
    # 生成统计图表
    df = pd.DataFrame(data)
    
    # 医院等级分布饼图
    class_dist = px.pie(
        df, names='hos_class', 
        title='医院等级分布', 
        labels={'hos_class': '等级'}
    )
    
    # 地址词云数据（需安装wordcloud）
    # from wordcloud import WordCloud
    # addresses = ' '.join(df['address'])
    # wordcloud = WordCloud().generate(addresses)
    
    return render_template(
        'dashboard.html',
        hospitals=data,
        class_chart=class_dist.to_html(),
        # wordcloud=wordcloud.to_svg()
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)