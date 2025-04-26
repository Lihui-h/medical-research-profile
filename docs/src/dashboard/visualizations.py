# src/dashboard/visualizations.py
import os
import plotly.express as px
import networkx as nx
from pyvis.network import Network
from pathlib import Path  # 用于处理文件路径

def plot_sentiment_trend(df):
    """情感趋势折线图（示例）"""
    fig = px.line(
        df.groupby("date").size().reset_index(name="count"),
        x="date", 
        y="count",
        title="医疗评价数量趋势",
        labels={"date": "日期", "count": "讨论帖数"}
    )
    fig.update_layout(
        template="plotly_dark",  # 暗黑主题
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
        plot_bgcolor="rgba(0,0,0,0)"
    ) 
    return fig

def draw_network_graph(df):
    """生成交互式传播网络图"""
    # 定义输出路径
    output_dir = Path("templates").resolve()  # 转换为绝对路径
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = r"E:\medtrust-guardian\templates\network.html"  # 硬编码测试路径

    G = nx.DiGraph()
    
    # 示例数据（需替换为实际数据源）
    G.add_nodes_from(["医院A", "媒体B", "用户群C"], 
                     size=30, 
                     title="点击查看详情", 
                     group="医疗机构")
    G.add_edges_from([("医院A", "媒体B", {"value": 0.8}),
                     ("媒体B", "用户群C", {"value": 0.6})])
    
    # 生成HTML可视化
    net = Network(height="600px", 
                 width="100%", 
                 bgcolor="#1a1a1a",  # 暗黑风格
                 font_color="white")
    net.from_nx(G)
    net.save_graph("templates/network.html")  # 保存到模板目录
    return "network.html"  # 返回HTML文件路径