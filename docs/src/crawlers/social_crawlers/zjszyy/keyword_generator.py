# src/crawlers/social_crawlers/zjszyy/keyword_generator.py
import itertools
from urllib.parse import quote

class KeywordGenerator:
    def __init__(self):
        # 基础关键词库
        self.base_keywords = [
            "浙江省中医院",
            "浙江省中医院 何强", "浙江省中医院 高祥福", "浙江省中医院 张弘",
            "浙江省中医院 施翔", "浙江省中医院 林胜友",
            "浙江省中医院 黄抒伟", "浙江省中医院 钱宇",
            "浙江省中医院 夏永良", "浙江省中医院 周秀扣",
            "浙江省中医院 陈意", "浙江省中医院 周郁鸿",
            "浙江省中医院 徐利", "浙江省中医院 吴蓓玲",
            "浙江省中医院 王真", "浙江省中医院 童培建",
            "浙江省中医院 陈晓洁", "浙江省中医院 方桂珍",
        ]

    def generate(self) -> list:
        """生成最终关键词列表"""
        return self.base_keywords.copy()

    def get_encoded_keywords(self) -> list:
        """生成URL编码后的关键词（供爬虫直接使用）"""
        return [quote(keyword) for keyword in self.generate()]