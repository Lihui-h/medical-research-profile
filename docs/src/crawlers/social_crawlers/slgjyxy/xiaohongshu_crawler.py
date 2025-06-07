import os
import re
import json
import time
import logging
from urllib.parse import quote
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from src.utils.api_client import OxylabsScraper
from src.crawlers.social_crawlers.slgjyxy.keyword_generator import KeywordGenerator
from supabase import create_client, Client

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("logs/xiaohongshu_crawler.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class XiaohongshuSpider:
    """小红书爬虫（增强代理稳定性版）"""
    
    def __init__(self, kw='浙江树人'):
        # 初始化参数
        self.keyword_tool = KeywordGenerator()
        self.final_keywords = self.keyword_tool.get_encoded_keywords()
        self.keyword = kw
        self.api_client = OxylabsScraper()
        self.base_url = "https://www.xiaohongshu.com"
        self.data = []
        
        # 初始化情感分析器
        self.sentiment_analyzer = WeightedSentimentAnalyzer()
        
        load_dotenv()
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY") 
        )
        
        # 树兰国际医学院专用配置
        self.org_code = "slgjyxy"
        self.institution_name = "树兰国际医学院"
        self.user_id = os.getenv("SUPABASE_USER_UUID_SLGJYXY")

    def run(self):
        """主运行逻辑"""
        logger.info("🚀 启动小红书数据采集引擎...")
        search_urls = self.generate_search_urls()
        
        total_count = 0
        for idx, url in enumerate(search_urls, 1):
            logger.info(f"▷ 处理URL [{idx}/{len(search_urls)}]: {url[:80]}...")
            
            # 调用API获取数据
            api_response = self.api_client.fetch_page(url)
            if not api_response.get("results"):
                continue
                
            # 解析列表页
            self.parse_list_page(api_response["results"][0]["content"])
            if not self.data:
                logger.warning("⚠️ 未获取到任何笔记数据")
                continue
            
            # 立即存储当前批次数据
            self._save_data()
            total_count += len(self.data)
            logger.info(f"✅ 已获取 {len(self.data)} 条笔记数据 | 累计: {total_count} 条")
            self.data.clear()
            
            # 合理延迟
            time.sleep(random.uniform(2.0, 4.0))
        
        logger.info(f"🏁 全部采集完成 | 总数据量: {total_count} 条")

    def generate_search_urls(self):
        """生成小红书搜索URL"""
        urls = []
        base_url = "https://www.xiaohongshu.com/search_result"
        
        for keyword in self.keyword_tool.generate():
            # 小红书搜索参数
            params = {
                "keyword": quote(keyword),
                "source": "web_explore_feed",
                "type": "note"  # 只搜索笔记类型
            }
            
            # 每页20条结果，爬取5页
            for page in range(1, 6):
                params["page"] = page
                query_str = "&".join([f"{k}={v}" for k, v in params.items()])
                urls.append(f"{base_url}?{query_str}")
        
        logger.info(f"生成 {len(urls)} 个小红书搜索URL")
        return urls

    def parse_list_page(self, html: str):
        """解析小红书搜索结果页"""
        soup = BeautifulSoup(html, "html.parser")
        
        # 小红书搜索结果结构可能有多种形式，尝试两种解析方式
        note_list = soup.select('div.note-item') or soup.select('div.card')
        
        if not note_list:
            logger.warning("⚠️ 未找到笔记卡片，可能页面结构已变更")
            return
        
        for note in note_list:
            item = {}
            try:
                # ==== 标题与内容 ====
                title_elem = note.select_one('.title, .content-title')
                content_elem = note.select_one('.desc, .content')
                
                item['title'] = title_elem.text.strip() if title_elem else "无标题"
                item['content'] = content_elem.text.strip() if content_elem else ""
                
                # ==== 作者信息 ====
                author_elem = note.select_one('.user-name, .author-info .name')
                item['author'] = author_elem.text.strip() if author_elem else "匿名用户"
                
                # ==== 互动数据 ====
                interactions = note.select('.interaction-item, .counts span')
                item['likes'] = interactions[0].text.strip() if len(interactions) > 0 else "0"
                item['collects'] = interactions[1].text.strip() if len(interactions) > 1 else "0"
                item['comments'] = interactions[2].text.strip() if len(interactions) > 2 else "0"
                
                # ==== 时间信息 ====
                time_elem = note.select_one('.time, .date')
                item['raw_post_time'] = time_elem.text.strip() if time_elem else "时间未标注"
                
                # ==== 详情链接 ====
                link_elem = note.select_one('a[href^="/explore/"]')
                if link_elem and link_elem.has_attr('href'):
                    item['detail_url'] = f"{self.base_url}{link_elem['href']}"
                else:
                    item['detail_url'] = "链接无效"
                
                # ==== 机构相关元数据 ====
                item.update({
                    'source': 'xiaohongshu',
                    'institution_name': self.institution_name,
                    'org_code': self.org_code,
                    'user_id': self.user_id
                })
                
                # 情感分析
                sentiment_result = self.sentiment_analyzer.analyze(
                    f"{item['title']} {item['content']}"
                )
                item['sentiment'] = sentiment_result[0]
                item['sentiment_score'] = sentiment_result[1]
                
                # 有效性校验
                required_keyword = '树人'
                valid_check = [
                    item.get('detail_url') and item['detail_url'] != "链接无效",
                    len(item.get('content', '')) > 10,
                    required_keyword in item.get('title', '') or required_keyword in item.get('content', '')
                ]
                
                if not all(valid_check):
                    reasons = []
                    if not valid_check[0]: reasons.append("无效链接")
                    if not valid_check[1]: reasons.append(f"内容过短({len(item.get('content',''))}字)")
                    if not valid_check[2]: reasons.append(f"未含关键词'{required_keyword}'")
                    logger.warning(f"跳过无效数据: {', '.join(reasons)}")
                    continue
                
                self.data.append(item)
                
            except Exception as e:
                logger.error(f"解析异常: {str(e)}")
                # 保存错误样本用于调试
                with open("error_note.html", "w", encoding="utf-8") as f:
                    f.write(str(note))

    def _save_data(self):
        """存储数据到Supabase"""
        if not self.data:
            logger.warning("⚠️ 无有效数据可存储")
            return
        
        try:
            # 批量插入并去重
            response = self.supabase.table('posts').upsert(
                self.data,
                on_conflict='detail_url'
            ).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"✅ 成功写入 {len(response.data)} 条数据")
            else:
                logger.warning("⚠️ 无新数据写入")
        except Exception as e:
            logger.error(f"存储失败: {str(e)}")

class WeightedSentimentAnalyzer:
    """小红书专用情感分析器（优化版）"""
    
    def __init__(self):
        # 负面词权重（针对教育领域优化）
        self.negative_weights = {
            "差评": -4, "失望": -3, "避雷": -4, "吐槽": -3, 
            "坑": -3, "不推荐": -3, "后悔": -3, "差劲": -4,
            "不行": -2, "不好": -2, "垃圾": -5, "投诉": -4
        }
        
        # 正面词权重
        self.positive_weights = {
            "推荐": +3, "满意": +3, "点赞": +3, "优秀": +4,
            "专业": +4, "超赞": +4, "值得": +3, "喜欢": +2,
            "好": +1, "棒": +2, "强": +2, "厉害": +3
        }
        
        # 教育领域特定词
        self.education_weights = {
            "师资": +3, "教学": +3, "学习氛围": +4, "实践机会": +3,
            "就业": +4, "考研": +3, "师资力量": +4, "校园环境": +2,
            "课程": +2, "专业设置": +3, "学费": -2, "宿舍条件": +1
        }
        
        self.thresholds = (-3, 3)  # (negative_threshold, positive_threshold)

    def calculate_score(self, text):
        """加权评分算法（教育领域优化版）"""
        score = 0
        
        # 负面词检测
        for word, weight in self.negative_weights.items():
            if word in text:
                score += weight * text.count(word)
                
        # 正面词检测
        for word, weight in self.positive_weights.items():
            if word in text:
                score += weight * text.count(word)
                
        # 教育领域关键词检测
        for word, weight in self.education_weights.items():
            if word in text:
                score += weight * text.count(word)
                
        # 表情符号增强
        if "👍" in text or "❤️" in text:
            score += 2
        if "👎" in text or "💔" in text:
            score -= 2
            
        return score

    def analyze(self, text):
        """情感分类"""
        score = self.calculate_score(text)
        if score <= self.thresholds[0]:
            return ("negative", score)
        elif score >= self.thresholds[1]:
            return ("positive", score)
        else:
            return ("neutral", score)

if __name__ == '__main__':
    import random
    load_dotenv()
    
    # 测试情感分析器
    analyzer = WeightedSentimentAnalyzer()
    test_cases = [
        "浙江树人的师资力量真的超棒！老师都很专业，学习氛围也很好 👍",
        "后悔选择了树兰，宿舍条件太差了，避雷！",
        "校园环境一般，但教学还可以，考研率不错",
        "垃圾学校，千万别来！👎"
    ]
    
    for text in test_cases:
        sentiment, score = analyzer.analyze(text)
        print(f"文本: {text}")
        print(f"情感: {sentiment}, 分数: {score}")
        print("-" * 50)
    
    # 运行爬虫
    spider = XiaohongshuSpider(kw='浙江树人')
    try:
        spider.run()
    except Exception as e:
        logger.error(f"爬虫异常终止: {str(e)}")