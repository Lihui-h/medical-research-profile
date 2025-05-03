# src/crawlers/social_crawlers/baidu_crawler.py
import os
import random
import time
import csv
import logging
from urllib.parse import quote
from pathlib import Path
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import requests
import json
from webdriver_manager.chrome import ChromeDriverManager
from requests.adapters import HTTPAdapter
from pymongo import MongoClient, UpdateOne
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
        self.fieldnames = [
            'title',
            'author',
            'content',
            'forum',      # 新增字段
            'post_time',  # 新增字段
            'detail_url',
            'reply_count' # 保留原有字段
        ]
        
        # MongoDB配置
        load_dotenv()
        self.client = MongoClient(os.getenv("MONGODB_URI"))
        self.social_db = self.client[os.getenv("SOCIAL_DB", "social_data")]
        self.collection = self.social_db[os.getenv("TIEBA_COLLECTION", "tieba_posts")]

    #核心方法
    def run(self):
        """主运行逻辑（整合搜索URL生成）"""
        logger.info("🚀 启动贴吧数据采集引擎...")

        try:
            search_urls = self.generate_search_urls()  # 调用新增的URL生成方法

            for idx, url in enumerate(search_urls, 1):
                self.data = []  # 🔴 新增：清空上一轮数据
                self.logger.info(f"▷ 正在处理第 {idx}/{len(search_urls)} 个搜索条件 | URL={url[:50]}...")

                # 调用API获取页面
                api_response = self.api_client.fetch_page(url)

                if not api_response.get("results"):
                    logger.warning(f"❗ 第 {idx} 个搜索条件无结果")
                    continue

                # 解析并存储数据
                self.parse_list_page(api_response["results"][0]["content"])
                self.crawl_details()

                # 动态延迟（3-7秒）
                time.sleep(random.uniform(3, 7))  

            # 存储最终数据
            if self.data:
                self._save_data()
                logger.info(f"✅ 采集完成 | 总计获取 {len(self.data)} 条有效数据")

        except Exception as e:
            logger.error(f"🔥 主流程异常终止: {str(e)}", exc_info=True)

        finally:
            self.close()
    
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
                item['content'] = content_elem.text.strip() if content_elem else "内容解析失败"

                # ===== 贴吧信息 =====
                forum_elem = post.select_one('a.p_forum font.p_violet')
                item['forum'] = forum_elem.text.strip() if forum_elem else "未知贴吧"

                # ===== 作者信息 =====
                author_elem = post.select_one('a[href^="/home/main"] font.p_violet')  # 精准定位作者
                item['author'] = author_elem.text.strip() if author_elem else "匿名用户"

                # ===== 时间信息 =====
                date_elem = post.select_one('font.p_date')
                item['post_time'] = date_elem.text.strip() if date_elem else "时间未标注"
                
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
        """统一存储入口（集成医疗内容过滤）"""
        from src.utils.data_filter import MedicalContentFilter  # 局部导入避免循环依赖

        if not self.data:
            self.logger.warning("⚠️ 暂无数据可存储")
            return
        
        try:
            # === 新增过滤逻辑 ===
            filter = MedicalContentFilter()
            filtered_data = [item for item in self.data if filter.is_medical_related(item)]

            if not filtered_data:
                self.logger.warning("🛑 过滤后无有效医疗数据")
                return
            
            # === 存储过滤后数据 ===
            mongo_result = self.save_to_mongodb(filtered_data)  # 修改传入参数
            csv_result = self.save_to_csv(filtered_data)         # 修改传入参数

            # === 更新日志信息 ===
            if mongo_result and csv_result:
                self.logger.info(
                    "💾 存储成功 | 原始数据: %d条 → 有效数据: %d条 (过滤率: %.1f%%)", 
                    len(self.data), 
                    len(filtered_data),
                    (1 - len(filtered_data)/len(self.data)) * 100
                )
            else:
                self.logger.warning("⚠️ 存储结果异常 | MongoDB: %s | CSV: %s", mongo_result, csv_result)
                
        except Exception as e:
            self.logger.error("💥 存储过程异常: %s", str(e), exc_info=True)

    def save_to_mongodb(self, data):
        """数据存储（含去重机制）"""
        if not data:
            logger.warning("⚠️ 无数据可存储")
            return False
            
        try:
            # 数据清洗与匿名化
            processed_data = [self._anonymize_data(item.copy()) for item in data]
            
            # 批量写入（自动去重）
            operations = [
                UpdateOne(
                    {"detail_url": item["detail_url"]},
                    {"$set": item},
                    upsert=True
                ) for item in processed_data
            ]
            result = self.collection.bulk_write(operations, ordered=False)
            logger.info(f"📦 数据写入完成 | 新增: {result.upserted_count} 更新: {result.modified_count} 总量: {len(data)}条")
            return True
        except Exception as e:
            logger.error(f"数据存储失败: {str(e)}")
            return False

    def save_to_csv(self, data):
        """本地备份（仅保存必要字段）"""
        save_dir = Path("data/raw/tieba")
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / f"{self.keyword}_贴吧数据.csv"
        
        try:
            # 自动获取所有字段（防止遗漏）
            all_fields = set()
            for item in data:
                all_fields.update(item.keys())

            # 写入文件
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=list(all_fields))
                writer.writeheader()
                writer.writerows(data)

                
            self.logger.info(f"💾 本地备份成功: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"CSV保存失败: {str(e)}")
            return False

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
        """生成复合搜索条件URL"""
        base_url = "https://tieba.baidu.com/f/search/res?ie=utf-8&qw={keyword}"
        return [base_url.format(keyword=kw) for kw in self.final_keywords]  # 直接使用编码后的关键词

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