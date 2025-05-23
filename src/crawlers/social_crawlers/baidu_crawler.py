# src/crawlers/social_crawlers/baidu_crawler.py
import os
import sys
import random
import time
import csv
import logging
import marshal
from urllib.parse import quote
from pathlib import Path
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import requests
import json
from webdriver_manager.chrome import ChromeDriverManager
from requests.adapters import HTTPAdapter
from supabase import create_client, Client
from dotenv import load_dotenv
from src.utils.api_client import OxylabsScraper  # 新增导入
from src.utils.keyword_generator import KeywordGenerator  # 新增导入

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("logs/tieba_crawler.log", encoding='utf-8'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class WeightedSentimentAnalyzer:
    def __init__(self):
        # 加载词库（可从文件读取）
        self.negative_weights = {
            "医疗事故": -5,
            "治残": -5,
            "垃圾": -4,
            "差评": -4,
            "焦虑": -3,
            "不明真相": -2,
            "不专业": -2,
            "不负责": -2,
            "生气": -2,
            "骗": -3,
            "可耻": -3,
        }
        self.positive_weights = {
            "专业": +3,
            "负责": +2,
            "经验丰富": +2,
            "好医生": +3,
            "好开心": +3,
            "有爱心": +2,
        }
        
        self.thresholds = (-3, 3)  # (negative_threshold, positive_threshold)

    def calculate_score(self, text):
        """加权评分算法"""
        score = 0
        # 负面词检测
        for word, weight in self.negative_weights.items():
            if word in text:
                score += weight * text.count(word)  # 按出现次数累加
        # 正面词检测
        for word, weight in self.positive_weights.items():
            if word in text:
                score += weight * text.count(word)
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

class TiebaSpider:
    """百度贴吧爬虫（增强代理稳定性版）"""
    #初始化方法
    def __init__(self, kw='浙江省中医院', max_page=2, delay=10):
        # 初始化参数
        self.keyword_tool = KeywordGenerator()  # 新增
        self.final_keywords = self.keyword_tool.get_encoded_keywords()  # 获取编码后的关键词
        self.logger = logging.getLogger(self.__class__.__name__)
        self.keyword = kw
        self.api_client = OxylabsScraper()
        self.base_url = "https://tieba.baidu.com"
        self.data = []
        # 初始化情感分析器（替换原snownlp相关代码）
        self.sentiment_analyzer = WeightedSentimentAnalyzer()
        
        
        load_dotenv()
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY") 
        )

    #核心方法
    def run(self):
        """新版主运行逻辑"""
        self.logger.info("🚀 启动贴吧数据采集引擎...")
        search_urls = self.generate_search_urls()
        
        total_count = 0
        for idx, url in enumerate(search_urls, 1):
            self.logger.info(f"▷ 处理URL [{idx}/{len(search_urls)}]: {url[:60]}...")

            # 调用API获取数据
            api_response = self.api_client.fetch_page(url)
            if not api_response.get("results"):
                continue

            # 解析列表页
            self.parse_list_page(api_response["results"][0]["content"])
            if not self.data:
                self.logger.warning("⚠️ 未获取到任何帖子数据")
                continue
            
            # 立即存储当前批次数据
            self._save_data()
            total_count += len(self.data)
            self.logger.info(f"✅ 已获取 {len(self.data)} 条帖子数据 | 累计: {total_count} 条")
            self.data.clear()  # 清空当前批次数据

            # 合理的延迟
            time.sleep(random.uniform(1.5, 3.5))  

        # 最终日记
        self.logger.info(f"🏁 全部采集完成 | 总数据量: {total_count} 条")

    
    def _run_static_mode(self):
        """静态解析模式专用流程"""
        logger.info("📄 进入静态解析模式")
        for page in range(1, self.max_page + 1):
            if not self.parse_list_page(page):
                break
            time.sleep(self.delay + random.uniform(1, 3))

        # 获取详情
        logger.info(f"🔍 开始处理 {len(self.data)} 条帖子详情")
        for idx, item in enumerate(self.data, 1):
            self.get_post_detail(item)
            time.sleep(random.uniform(0.8, 2.2))

    def parse_list_page(self, html: str):
        """解析贴吧列表页（适配新版页面结构）"""
        soup = BeautifulSoup(html, "html.parser")
        post_list = soup.select('div.s_post')

        for post in post_list:
            item = {}
            try:
                # ===== 标题与链接 =====
                title_elem = post.select_one('span.p_title a.bluelink')
                item['title'] = title_elem.text.strip() if title_elem else "无标题"

                # 构建完整链接（需处理相对路径）
                if title_elem and title_elem.has_attr('href'):
                    item['detail_url'] = f"https://tieba.baidu.com{title_elem['href'].split('?')[0]}"  # 去除参数保留纯净URL
                else:
                    item['detail_url'] = "链接无效"
                
                # ===== 正文内容 =====
                content_elem = post.select_one('div.p_content')
                raw_content = content_elem.text.strip() if content_elem else "内容解析失败"
                item['content'] = raw_content[:500]  # 限制长度防止超字段限制

                # ===== 贴吧信息 =====
                forum_elem = post.select_one('a.p_forum font.p_violet')
                item['forum'] = forum_elem.text.strip() if forum_elem else "未知贴吧"

                # ===== 作者信息 =====
                author_elem = post.select_one('a[href^="/home/main"] font.p_violet')  # 精准定位作者
                item['author'] = author_elem.text.strip() if author_elem else "匿名用户"

                # ===== 时间信息 =====
                date_elem = post.select_one('font.p_date')
                item['raw_post_time'] = date_elem.text.strip() if date_elem else "时间未标注"

                item.update({
                    #固定字段
                    'source': 'baidu_tieba',
                    'institution_name': '浙江省中医院',
                    'org_code': 'zjszyy',
                    'user_id': os.getenv("SUPABASE_USER_UUID")
                })

                sentiment_result = self.sentiment_analyzer.analyze(raw_content)
                # 如果返回元组（标签，分数）
                item['sentiment'] = sentiment_result[0]  # 取情感标签
                item['sentiment_score'] = sentiment_result[1]  # 取情感分数

                # ==== 新增有效性校验 ====
                required_keyword = '浙江省中医院'
                valid_check = [
                    item.get('detail_url') and item['detail_url'] != "链接无效",  # 检查有效链接
                    len(item.get('content', '')) > 10,                         # 内容长度限制
                    required_keyword in item.get('title', '') or required_keyword in item.get('content', '')  # 关键词匹配
                ]
                if not all(valid_check):
                    log_msg = f"跳过无效数据 | 原因："
                    reasons = []
                    if not valid_check[0]:
                        reasons.append("无效链接")
                    if not valid_check[1]:
                        reasons.append(f"内容过短（{len(item.get('content',''))}字）") 
                    if not valid_check[2]:
                        reasons.append(f"未包含关键词'{required_keyword}'")

                    self.logger.warning(log_msg + "，".join(reasons))
                    continue
                
                # 追加到数据列表
                self.data.append(item)
            except Exception as e:
                self.logger.error(f"解析异常: {str(e)}")
                # 保存错误样本用于调试
                with open("error_post.html", "w", encoding="utf-8") as f:
                    f.write(str(post))
            
        if not self.data:
            self.logger.warning("⚠️ 未解析到任何帖子数据，请检查HTML结构或选择器")

    def crawl_details(self):
        """批量获取详情页"""
        for idx, item in enumerate(self.data, 1):
            detail_response = self.api_client.fetch_page(item['detail_url'])
            if detail_html := detail_response.get("results", [{}])[0].get("content"):
                self.parse_detail(item, detail_html)
            self.logger.info(f"进度: {idx}/{len(self.data)}")
            time.sleep(1.5)  # 控制请求频率

    def parse_detail(self, item: dict, html: str):
        """解析详情页"""
        soup = BeautifulSoup(html, "html.parser")
        content_div = soup.find('div', class_='d_post_content')
        item['content'] = content_div.text.strip() if content_div else ''

    def get_post_detail(self, item):
        """通过 API 获取详情页内容"""
        try:
            # 调用 API 获取详情页
            detail_response = self.api_client.fetch_page(item['detail_url'])

            # 校验 API 响应
            if not detail_response.get("results"):
                logger.error(f"API 响应异常: {detail_response}")
                return
            
            # 提取 HTML 内容
            detail_html = detail_response["results"][0].get("content", "")
            if not detail_html:
                logger.warning(f"详情页内容为空: {item['detail_url']}")
                return
            
            # 解析内容
            soup = BeautifulSoup(detail_html, "html.parser")
            content_div = soup.find('div', class_='d_post_content')
            item['content'] = content_div.text.strip() if content_div else ''
            
            
            # 随机延迟（1-3秒）
            time.sleep(random.uniform(1, 3))
            
        except Exception as e:
            logger.error(f"详情页获取失败: {str(e)}")

    #存储方法
    def _save_data(self):
        """直接存储到Supabase"""
        if not self.data:
            self.logger.warning("⚠️ 无有效数据可存储")
            return
        
        try:
            # 批量插入并去重
            response = self.supabase.table('posts').upsert(
                self.data,
                on_conflict='detail_url'
            ).execute()
            
            if len(response.data) > 0:
                self.logger.info(f"✅ 成功写入 {len(response.data)} 条数据")
            else:
                self.logger.warning("⚠️ 无新数据写入")
        except Exception as e:
            self.logger.error(f"存储失败: {str(e)}")

    #工具方法
    def _anonymize_data(self, item):
        """数据匿名化处理"""
        # 移除用户ID字段（如果存在）
        item.pop('user_id', None)
        
        # 时间模糊处理（保留到天）
        if 'publish_time' in item and isinstance(item['publish_time'], str):
            item['publish_time'] = item['publish_time'].split(' ')[0]
        
        # 敏感词替换
        sensitive_terms = {'艾滋病': '某传染病', '乙肝': '某病毒性肝炎'}
        for term, replacement in sensitive_terms.items():
            item['content'] = item['content'].replace(term, replacement)
        return item

    def generate_search_urls(self):
        """生成带分页的搜索URL"""
        base_url = "https://tieba.baidu.com/f/search/res"
        urls = []
        for keyword in self.keyword_tool.generate():  # 获取原始关键词
            # 将关键词转为GBK编码
            try:
                gbk_bytes = keyword.encode('gbk', errors='strict')
            except UnicodeEncodeError:
                self.logger.error(f"关键词'{keyword}'无法用GBK编码，已跳过")
                continue

            encoded_kw = ''.join([f'%{b:02X}' for b in gbk_bytes])

            params = {
                "isnew": 1,
                'kw': "",
                "qw": encoded_kw,
                'rn': 10,  # 每页10条结果
                "un": "",
                "only_thread": 0,  # 包含主题帖和回复
                "sm": 1,
                "sd": "",
                "ed": ""
            }

            # 每页10条结果(rn=10)，爬取10页
            for page in range(0, 10):
                params["pn"] = page + 1  # 分页从1开始
                query = '&'.join([f"{k}={v}" for k, v in params.items()])
                urls.append(f"{base_url}?{query}")

        logger.info(f"Generated {len(urls)} search URLs")
        return urls
    



    #资源管理
    def close(self):
        """资源清理"""
        self.logger.info("爬虫进程结束")

#主程序
if __name__ == '__main__':
    load_dotenv()
    spider = TiebaSpider(kw='浙江省中医院')
    try:
        # 完整执行流程
        spider.run()  # 调用主运行方法
        logger.info("🎉 爬取任务完成！")
    finally:
        spider.close()  # 确保关闭WebDriver