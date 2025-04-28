# src/crawlers/shsj_gov_crawler.py
"""
上海市松江区人民政府-医疗机构信息采集爬虫
接口规范文档：接口调用说明_xml_7210.docx
"""

import logging
import xml.etree.ElementTree as ET
import requests
import time
from typing import Dict, List, Optional
from pathlib import Path

# -------------------- 配置区域 --------------------
API_URL = "https://data.sh.gov.cn/interface/7210/12225"  # 需替换为真实接口URL
API_TOKEN = "4e8afb83ba4cbbdf95060eb0809e64f4"    # 需替换为有效Token
REQUEST_LIMIT = 100                               # 单次请求最大数据量
MAX_RETRIES = 3                                   # 请求失败最大重试次数
BASE_DELAY = 1.5                                  # 基础请求延迟(秒)
TIMEOUT = (30, 120)                                # 连接/读取超时时间
OUTPUT_DIR = Path("data/processed/songjiang")     # 数据输出目录

# -------------------- 初始化 --------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/shsj_crawler.log"),
        logging.StreamHandler()
    ]
)

# -------------------- XML工具函数 --------------------
def build_xml_request(
    address: str = "松江区", # 强制默认地址
    name: str = "松江区",
    limit: int = REQUEST_LIMIT,
    offset: int = 0
) -> bytes:
    """
    构建符合接口规范的XML请求体
    :param address: 地址关键词（可选）
    :param name: 机构名称关键词（可选）
    :param limit: 单次请求数量
    :param offset: 分页偏移量
    :return: UTF-8编码的XML字节流
    """
    try:
        root = ET.Element("map")
        ET.SubElement(root, "address").text = address
        ET.SubElement(root, "name").text = name
        ET.SubElement(root, "limit").text = str(limit)
        ET.SubElement(root, "offset").text = str(offset)
        return ET.tostring(root, encoding="utf-8", method="xml")
    except ET.ParseError as e:
        logging.error(f"XML构建失败: {str(e)}")
        raise

def parse_xml_response(xml_content: bytes) -> Optional[Dict]:
    """
    解析XML响应内容
    :param xml_content: 原始响应字节流
    :return: 结构化数据字典，解析失败返回None
    """
    try:
        root = ET.fromstring(xml_content)
        
        # 基础响应字段
        code = root.findtext("code", default="999999")
        message = root.findtext("message", default="Unknown error")
        
        # 数据节点校验
        data_node = root.find("data/Result")
        if not data_node:
            logging.warning("响应缺少有效数据节点")
            return None
            
        state = data_node.findtext("state", default="false")
        total = int(data_node.findtext("total", default="0"))
        
        # 数据条目提取
        entries = []
        for entry in data_node.findall("datas/Data"):
            entries.append({
                "name": entry.findtext("name", default=""),
                "address": entry.findtext("address", default=""),
                "order": entry.findtext("order", default="")
            })
            
        return {
            "code": code,
            "message": message,
            "state": state.lower() == "true",
            "total": total,
            "data": entries
        }
    except ET.ParseError as e:
        logging.error(f"XML解析失败: {str(e)}")
        return None

# -------------------- 核心爬取类 --------------------
class SongjiangMedicalCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/xml",
            "cache-control": "no-cache",
            "token": API_TOKEN
        })
        self.session.mount('https://', requests.adapters.HTTPAdapter(
            max_retries=MAX_RETRIES,
            pool_connections=20,
            pool_maxsize=100
        ))
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def _safe_request(
        self,
        xml_body: bytes,
        current_retry: int = 0
    ) -> Optional[requests.Response]:
        """
        带重试机制的请求封装
        :param xml_body: XML请求体
        :param current_retry: 当前重试次数
        """
        try:
            response = self.session.post(
                API_URL,
                data=xml_body,
                timeout=TIMEOUT
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if current_retry < MAX_RETRIES:
                delay = BASE_DELAY * (2 ** current_retry)
                logging.warning(f"请求失败，第{current_retry+1}次重试 - {str(e)}")
                time.sleep(delay)
                return self._safe_request(xml_body, current_retry + 1)
            logging.error(f"请求最终失败: {str(e)}")
            return None

    def fetch_page(
        self,
        offset: int = 0,
        address: str = "",
        name: str = ""
    ) -> Optional[Dict]:
        """
        获取单页数据
        :param offset: 分页偏移量
        :param address: 地址关键词
        :param name: 机构名称关键词
        """
        try:
            xml_body = build_xml_request(
                address=address,
                name=name,
                offset=offset
            )
            response = self._safe_request(xml_body)
            if not response:
                return None
            return parse_xml_response(response.content)
        except Exception as e:
            logging.error(f"单页请求异常: {str(e)}")
            return None

    def crawl_all(
        self,
        address_filter: str = "",
        name_filter: str = ""
    ) -> List[Dict]:
        """
        全量爬取入口
        :param address_filter: 地址过滤关键词
        :param name_filter: 名称过滤关键词
        :return: 医疗机构数据列表
        """
        all_data = []
        offset = 0
        total_records = 0
        
        while True:
            # 获取当前页数据
            result = self.fetch_page(
                offset=offset,
                address=address_filter,
                name=name_filter
            )
            
            # 终止条件判断
            if not result:
                logging.warning("获取到空响应，终止采集")
                break
            if not result.get("state"):
                logging.error(f"接口状态异常: {result.get('message')}")
                break
            if result["total"] == 0:
                logging.info("无更多数据")
                break
                
            # 处理有效数据
            current_data = result.get("data", [])
            if not current_data:
                logging.info("当前页无有效数据")
                break
                
            all_data.extend(current_data)
            total_records += len(current_data)
            offset += REQUEST_LIMIT
            
            # 进度日志
            logging.info(
                f"进度: 已获取 {total_records} 条 | 分页位置 {offset}"
                f" | 接口报告总数 {result['total']}"
            )
            
            # 动态延迟控制
            time.sleep(BASE_DELAY * (1 + (offset // 1000)))
            
        return all_data

    def save_to_json(self, data: List[Dict]) -> None:
        """
        保存数据到JSON文件
        :param data: 医疗机构数据列表
        """
        import json
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = OUTPUT_DIR / f"medical_{timestamp}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logging.info(f"数据已保存至: {filename}")

# -------------------- 主执行流程 --------------------
if __name__ == "__main__":
    crawler = SongjiangMedicalCrawler()
    
    try:
        logging.info("=== 开始采集松江区医疗机构数据 ===")
        
        # 示例：采集所有"妇幼"相关机构
        medical_data = crawler.crawl_all(name_filter="妇幼")
        
        if medical_data:
            crawler.save_to_json(medical_data)
            logging.info(f"成功采集 {len(medical_data)} 条数据")
        else:
            logging.warning("未获取到有效数据")
            
    except KeyboardInterrupt:
        logging.warning("用户中断操作")
    except Exception as e:
        logging.error(f"主流程异常: {str(e)}", exc_info=True)
    finally:
        crawler.session.close()
        logging.info("=== 采集任务结束 ===")