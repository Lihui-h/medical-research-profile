# src/utils/api_client.py
import json
import requests
import logging
from dotenv import load_dotenv
import os
import time

load_dotenv()

class OxylabsScraper:
    """Oxylabs Web 爬虫 API 客户端"""
    
    def __init__(self):
        self.api_url = "https://realtime.oxylabs.io/v1/queries"
        self.auth = (os.getenv("OXYLABS_USER"), os.getenv("OXYLABS_PASS"))
        self.logger = logging.getLogger(self.__class__.__name__)

    def fetch_page(self, url: str, max_retries=3) -> dict:
        """通用页面抓取方法"""
        payload = {
            "source": "universal",
            "url": url,
            "geo_location": "cn"
        }
        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    self.api_url,
                    auth=self.auth,
                    json=payload,
                    timeout=30  # 设置超时时间
                )
                resp.raise_for_status()
                # 新增调试日志
                self.logger.debug(f"API原始响应内容:\n{json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
                return resp.json()
            except requests.exceptions.Timeout:
                self.logger.warning(f"API请求超时，第{attempt+1}次重试...")
                time.sleep(2 ** attempt)  # 指数退避
            except Exception as e:
                self.logger.error(f"API请求失败: {str(e)}")
                return {}
        return {}