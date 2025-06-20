# src/crawlers/social_crawlers/slgjyxy/xiaohongshu_crawler.py
import os
import re
import json
import time
import random
import logging
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime, timedelta
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from src.utils.api_client import OxylabsScraper
from src.crawlers.social_crawlers.slgjyxy.keyword_generator import KeywordGenerator
from supabase import create_client, Client

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/xiaohongshu_crawler.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class XiaohongshuSpider:
    """小红书两阶段爬虫（2025优化版）"""
    
    def __init__(self, kw='浙江树人'):
        # 初始化参数
        self.keyword_tool = KeywordGenerator()
        self.keyword = kw
        self.api_client = OxylabsScraper()
        self.base_url = "https://www.xiaohongshu.com"
        self.search_url = "https://www.xiaohongshu.com/search_result?keyword=%25E6%25B5%2599%25E6%25B1%259F%25E6%25A0%2591%25E4%25BA%25BA&source=web_explore_feed"
        self.data = []
        self.detail_urls = []  # 存储需要爬取的详情页URL
        
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
        logger.info("启动小红书数据采集引擎...")
        
        # 第一阶段：获取搜索结果页中的详情链接
        logger.info(f"爬取固定搜索页: {self.search_url}")
            
            # 调用API获取搜索页数据
        api_response = self.api_client.fetch_page(self.search_url)
        if not api_response.get("results"):
            logger.warning("API响应为空，跳过")
            return
                
        # 解析搜索页，提取详情页URL
        self.parse_search_page(api_response["results"][0]["content"])
            
        # 合理延迟
        time.sleep(random.uniform(2.0, 4.0))
        
        logger.info(f"从搜索页提取到 {len(self.detail_urls)} 个详情页链接")
        
        # 第二阶段：爬取详情页内容
        total_details = len(self.detail_urls)
        for idx, url in enumerate(self.detail_urls, 1):
            logger.info(f"爬取详情页 [{idx}/{total_details}]: {url[:80]}...")
            
            # 调用API获取详情页数据
            detail_response = self.api_client.fetch_page(url)
            if not detail_response.get("results"):
                logger.warning("详情页API响应为空，跳过")
                continue
                
            # 解析详情页内容
            self.parse_detail_page(detail_response["results"][0]["content"], url)
            
            # 更长的随机延迟，模拟人工操作
            delay = random.uniform(3.0, 8.0)
            logger.debug(f"随机延迟 {delay:.1f} 秒")
            time.sleep(delay)
            
            # 每处理5个详情页保存一次数据
            if idx % 5 == 0:
                self._save_data()
        
        # 保存剩余数据
        if self.data:
            self._save_data()
        
        logger.info(f"全部采集完成 | 总数据量: {len(self.data)} 条")

    def parse_search_page(self, html: str):
        """解析搜索结果页，提取详情页链接"""
        soup = BeautifulSoup(html, "html.parser")
        
        # 方法1：直接定位链接元素（最可靠）
        links = soup.find_all('a', href=re.compile(r'/search_result/'))

        if links:
            logger.info(f"直接找到 {len(links)} 个链接")
            for link in links:
                try:
                    if link.has_attr('href'):
                        href = link['href']
                        if not href.startswith("http"):
                            href = urljoin(self.base_url, href)
                        self.detail_urls.append(href)
                        logger.info(f"添加详情页: {href}")
                    else:
                        logger.warning("链接缺少href属性")
                except Exception as e:
                    logger.error(f"处理链接异常: {str(e)}")
            return

        # 方法2：使用更广泛的搜索
        logger.warning("直接定位链接失败，尝试更广泛的搜索...")
        all_links = soup.find_all('a')
        found_links = 0

        for link in all_links:
            try:
                if link.has_attr('href') and "/search_result/" in link['href']:
                    href = link['href']
                    if not href.startswith("http"):
                        href = urljoin(self.base_url, href)
                    self.detail_urls.append(href)
                    found_links += 1
                    logger.info(f"添加详情页: {href}")
            except Exception as e:
                logger.error(f"处理链接异常: {str(e)}")

        if found_links:
            logger.info(f"通过广泛搜索找到 {found_links} 个链接")
            return
        
        # 方法3：最后尝试
        logger.warning("所有链接查找方法失败，尝试提取data-v-*元素")
        note_items = []

        # 查找所有包含data-v-属性的元素
        all_elements = soup.find_all(True)
        for element in all_elements:
            if element.name in ['section', 'div']:
                for attr_name in element.attrs:
                    if attr_name.startswith('data-v-'):
                        note_items.append(element)
                        break
            
        if not note_items:
            logger.warning("未找到笔记卡片，尝试备用选择器...")
            # 尝试类名选择器
            note_items = soup.select('section.note-item, div.note-item, div.feed-item')
        
        if not note_items:
            logger.warning("所有选择器均失败，可能页面结构已变更")
            return
        
        logger.info(f"找到 {len(note_items)} 个笔记卡片")
        
        for item in note_items:
            try:
                # 尝试在容器内查找链接
                link_element = item.find('a', href=lambda x: x and "/search_result/" in x)
                
                if link_element and link_element.has_attr('href'):
                    href = link_element['href']
                    
                    # 清理URL参数，保留关键部分
                    parsed = urlparse(href)
                    path = parsed.path
                    
                    # 提取关键参数（如note_id）
                    note_id = path.split('/')[-1] if path else None
                    query_params = parse_qs(parsed.query)
                    
                    # 构建标准化的详情页URL
                    if note_id:
                        # 保留必要的参数
                        essential_params = {
                            "source": "web_explore_feed",
                            "xsec_source": "pc_search"
                        }
                        
                        # 如果有token则保留
                        if 'xsec_token' in query_params:
                            essential_params['xsec_token'] = query_params['xsec_token'][0]
                        
                        # 构建查询字符串
                        query_str = "&".join([f"{k}={v}" for k, v in essential_params.items()])
                        
                        # 构建完整URL
                        detail_url = f"{self.base_url}/explore/{note_id}?{query_str}"
                        self.detail_urls.append(detail_url)
                        logger.debug(f"添加详情页: {detail_url}")
                    else:
                        logger.warning(f"无法从链接提取note_id: {href}")
                else:
                    logger.warning("未找到有效链接元素")
                    
            except Exception as e:
                logger.error(f"解析搜索页异常: {str(e)}")

    def parse_detail_page(self, html: str, url: str):
        """解析详情页内容"""
        soup = BeautifulSoup(html, "html.parser")
        item = {"detail_url": url}
        
        try:
            # ==== 标题 ====
            title_elem = soup.select_one('h1.title, div.title, h2.title')
            item['title'] = title_elem.text.strip() if title_elem else "无标题"
            
            # ==== 内容 ====
            content_elem = soup.select_one('div.content, div.note-content, span.note-text')
            item['content'] = content_elem.text.strip() if content_elem else ""
            
            # ==== 作者 ====
            author_elem = soup.select_one('a.name, div.author-info, span.username')
            item['author'] = author_elem.text.strip() if author_elem else "匿名用户"
            
            # ==== 发布时间 ====
            time_elem = soup.select_one('time.date, span.data, div.date')
            if time_elem:
                # 转换相对时间（如"3天前"）
                raw_time = time_elem.text.strip()
                item['raw_post_time'] = self.parse_relative_time(raw_time)
            else:
                item['raw_post_time'] = datetime.now().strftime("%Y-%m-%d")
            
            # ==== 互动数据 ==== (使用更精确的方法)
            interactions = self.extract_interaction_data(soup)
            item.update(interactions)
            
            # ==== 机构相关元数据 ====
            item.update({
                'source': 'xiaohongshu',
                'institution_name': self.institution_name,
                'org_code': self.org_code,
                'user_id': self.user_id
            })
            
            # 情感分析
            full_text = f"{item['title']} {item['content']}"
            sentiment_result = self.sentiment_analyzer.analyze(full_text)
            item['sentiment'] = sentiment_result[0]
            item['sentiment_score'] = sentiment_result[1]
            
            # 有效性校验
            required_keywords = ['树人', '树兰', '树大', '树院']
            has_keyword = any(kw in full_text for kw in required_keywords)
            
            valid_check = [
                len(item.get('content', '')) > 20,
                has_keyword
            ]
            
            if not all(valid_check):
                reasons = []
                if not valid_check[0]: reasons.append(f"内容过短({len(item.get('content',''))}字)")
                if not valid_check[1]: reasons.append("未含关键词")
                logger.warning(f"跳过无效数据: {', '.join(reasons)}")
                return
            
            self.data.append(item)
            logger.info(f"成功解析详情页: {item['title'][:20]}...")
            
        except Exception as e:
            logger.error(f"解析详情页异常: {str(e)}")
            # 保存错误页用于调试
            timestamp = int(time.time())
            with open(f"error_detail_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(html)

    def extract_interaction_data(self, soup):
        """精确提取互动数据（点赞、收藏、评论）"""
        interactions = {}
        
        # 点赞数 - 使用精确选择器
        likes = soup.select_one('span.like-wrapper span.count, span.like-count')
        interactions['likes'] = self.convert_count(likes.text.strip()) if likes else 0
        
        # 收藏数 - 使用精确选择器
        collects = soup.select_one('span.collect-wrapper span.count, span.collect-count')
        interactions['collects'] = self.convert_count(collects.text.strip()) if collects else 0
        
        # 评论数 - 使用精确选择器
        comments = soup.select_one('span.chat-wrapper span.count, span.comment-count')
        interactions['comments'] = self.convert_count(comments.text.strip()) if comments else 0
        
        return interactions

    def parse_relative_time(self, time_str):
        """转换相对时间为标准日期格式"""
        now = datetime.now()
        
        if "分钟" in time_str:
            mins = int(re.search(r'\d+', time_str).group())
            return (now - timedelta(minutes=mins)).strftime("%Y-%m-%d")
        elif "小时" in time_str:
            hours = int(re.search(r'\d+', time_str).group())
            return (now - timedelta(hours=hours)).strftime("%Y-%m-%d")
        elif "天" in time_str:
            days = int(re.search(r'\d+', time_str).group())
            return (now - timedelta(days=days)).strftime("%Y-%m-%d")
        elif "周" in time_str:
            weeks = int(re.search(r'\d+', time_str).group())
            return (now - timedelta(weeks=weeks)).strftime("%Y-%m-%d")
        elif "月" in time_str:
            months = int(re.search(r'\d+', time_str).group())
            return (now - timedelta(days=months*30)).strftime("%Y-%m-%d")
        elif "年" in time_str:
            years = int(re.search(r'\d+', time_str).group())
            return (now - timedelta(days=years*365)).strftime("%Y-%m-%d")
        else:
            # 尝试解析标准日期格式
            try:
                datetime.strptime(time_str, "%Y-%m-%d")
                return time_str
            except:
                return datetime.now().strftime("%Y-%m-%d")

    def convert_count(self, text):
        """转换互动计数文本为数字"""
        if '万' in text:
            num = float(re.search(r'[\d.]+', text).group())
            return int(num * 10000)
        elif '千' in text:
            num = float(re.search(r'[\d.]+', text).group())
            return int(num * 1000)
        else:
            return int(re.search(r'\d+', text).group()) if re.search(r'\d+', text) else 0

    def _save_data(self):
        """存储数据到Supabase"""
        if not self.data:
            logger.warning("无有效数据可存储")
            return
        
        try:
            # 批量插入并去重
            response = self.supabase.table('posts').upsert(
                self.data,
                on_conflict='detail_url'
            ).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"成功写入 {len(response.data)} 条数据")
                self.data = []  # 清空已保存数据
            else:
                logger.warning("无新数据写入")
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
    load_dotenv()
    
    # 运行爬虫
    spider = XiaohongshuSpider(kw='浙江树人')
    try:
        spider.run()
    except Exception as e:
        logger.error(f"爬虫异常终止: {str(e)}")