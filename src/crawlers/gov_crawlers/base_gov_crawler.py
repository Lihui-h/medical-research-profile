# src/crawlers/gov_crawlers/base_gov_crawler.py
import json
import logging
import requests
from pathlib import Path
from dotenv import load_dotenv
import os

class BaseGovCrawler:
    """政府数据爬虫基类（终极编码修复版）"""
    
    def __init__(self):
        self._load_config()
        self._init_logger()
        self.proxy_enabled = False  # 默认禁用代理
        self.session = requests.Session()  # 创建独立会话
        self.session.trust_env = False  # 屏蔽系统代理

    def _init_logger(self):
        """初始化日志系统"""
        self.logger = logging.getLogger(self.__class__.__name__)

        # 避免重复添加处理器
        if not self.logger.handlers:
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            self.logger.addHandler(stream_handler)
            self.logger.propagate = False  # 防止日志重复
            
        self.logger.setLevel(logging.INFO)

    def _load_config(self):
        """加载环境变量"""
        load_dotenv()
        self.BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

    def safe_request(self, method: str, url: str, **kwargs):
        """安全请求方法（完全控制编码）"""
        try:
            # 生成基础请求头
            headers = kwargs.pop("headers", self.generate_headers())
            headers.update({
                "Content-Type": "application/json; charset=utf-8",
                "Accept-Charset": "utf-8"
            })
            
            # 处理JSON数据编码
            if "json" in kwargs:
                json_str = json.dumps(kwargs["json"], ensure_ascii=False)
                kwargs["data"] = json_str.encode("utf-8")
                del kwargs["json"]  # 必须删除原参数
                self.logger.debug(f"JSON编码结果: {json_str}")

            # 发送请求
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs
            )
            response.encoding = "utf-8"  # 强制响应解码
            response.raise_for_status()
            return response
        except Exception as e:
            self.logger.error(f"请求失败: {str(e)}")
            return None

    def generate_headers(self):
        """生成动态请求头"""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",  # 新增此行
            "token": os.getenv("SH_DATA_TOKEN", "")
        }
