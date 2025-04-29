# src/utils/keyword_generator.py
import itertools
from urllib.parse import quote

class KeywordGenerator:
    def __init__(self):
        # 基础关键词库
        self.base_keywords = [
            "省中", "浙江中医院", "浙中医",
            "省中 何强", "省中 高祥福", "省中 张弘",
            "省中 施翔", "省中 林胜友",
            "省中 黄抒伟", "省中 钱宇",
            "省中 夏永良", "省中 周秀扣"
        ]
        # 地理限定词
        self.geo_terms = ["浙江", "湖滨", "下沙"]

    def generate(self, enable_geo=True) -> list:
        """生成最终关键词列表"""
        if not enable_geo:
            return self.base_keywords.copy()

        # 动态组合地理词与基础词
        combinations = itertools.product(self.geo_terms, self.base_keywords)
        return [' '.join(pair) for pair in combinations]

    def get_encoded_keywords(self) -> list:
        """生成URL编码后的关键词（供爬虫直接使用）"""
        return [quote(keyword) for keyword in self.generate()]