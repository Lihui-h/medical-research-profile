# src/crawlers/social_crawlers/slgjyxy/keyword_generator.py
import itertools
from urllib.parse import quote

class KeywordGenerator:
    def __init__(self):
        # 基础关键词库
        self.base_keywords = [
            "树兰国际医学院", "浙江树人大学",
            "浙江树人学院", "树兰医学院", "浙江树人"
        ]

    def generate(self) -> list:
        """生成最终关键词列表"""
        return self.base_keywords.copy()

    def get_encoded_keywords(self) -> list:
        """生成URL编码后的关键词（供爬虫直接使用）"""
        return [quote(keyword) for keyword in self.generate()]