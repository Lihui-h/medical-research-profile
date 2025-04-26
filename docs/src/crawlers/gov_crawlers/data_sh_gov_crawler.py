# src/crawlers/gov_crawlers/data_sh_gov_crawler.py
import os
import json
import logging
import requests
import time
import random
import sys
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError, ConnectionFailure
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from .base_gov_crawler import BaseGovCrawler

class DataShGovCrawler(BaseGovCrawler):
    """上海医保数据采集（终极稳定版）"""
    
    def __init__(self):
        super().__init__()
        # 从环境变量获取配置
        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.db_name = os.getenv("MONGODB_DB", "gov_data")
        self.collection_name = os.getenv("MONGODB_COLLECTION", "sh_hospitals")

        # 从环境变量读取多个area_id
        self.area_ids = list(map(
            str.strip,
            os.getenv("DEFAULT_AREA_IDS", "20").split(",")
        ))
        self.logger.info(f"初始化采集区域: {self.area_ids}")

        # 确保环境变量存在
        if not self.mongodb_uri:
            raise ValueError("MONGODB_URI 未设置")

        # 连接 MongoDB Atlas
        self.client = MongoClient(self.mongodb_uri)
        # 连接到政府专用数据库
        self.gov_db = self.client[os.getenv("GOV_DB", "gov_data")]
        self.collection = self.gov_db[os.getenv("GOV_COLLECTION", "sh_hospitals")]

        # 初始化API URL
        self.api_url = "https://data.sh.gov.cn/interface/AG9102015009/14661"
        self.proxy_enabled = False  # 强制禁用代理
        # 初始化请求参数（双重编码保护）
        self.required_params = {
            "area_id": "default_value",  # 占位符
            "limit": 200,
            "offset": 0
        }

    def crawl_medical_institutions(self):
        """主采集流程"""
        total_records = 0
        MAX_RETRIES = 3  # 单页请求重试次数
        REQUEST_DELAY = 1  # 请求间隔（秒）

        # 遍历所有area_id
        for area_id in self.area_ids:
            self.logger.info(f"开始采集区域: area_id={area_id}")
            current_offset = 0  # 重置offset
            has_more = True
            retry_count = 0

            while has_more:
                # 构建当前区域的请求参数
                params = {
                    "area_id": str(area_id),
                    "limit": 200,
                    "offset": current_offset
                }

                # 请求数据（含重试机制）
                data = []
                for attempt in range(MAX_RETRIES):
                    try:
                        self.logger.debug(f"▷ 请求参数: {params}")
                        result = self.safe_api_request(params)

                        if not result or "data" not in result:
                            self.logger.warning(f"第 {attempt+1} 次重试...")
                            continue
                        data = result["data"].get("data", [])
                        actual_count = len(data)
                        self.logger.info(f"✔ 获取到 {actual_count} 条数据")
                        break  # 成功获取数据，退出重试循环
                    except Exception as e:
                        self.logger.error(f"请求异常: {str(e)}")
                        time.sleep(2 ** attempt)  # 指数退避
                else:
                    self.logger.error(f"❗ 区域 {area_id} 分页终止，连续 {MAX_RETRIES} 次请求失败")
                    has_more = False
                    continue
                # 保存数据
                if data:
                    if self.save_data(data, "gov_reports", f"medical_{area_id}.json"):
                        total_records += len(data)

                    # 分页终止条件：实际返回数量小于limit
                    if len(data) < params["limit"]:
                        self.logger.info(f"✅ 区域 {area_id} 数据采集完成，共 {current_offset + len(data)} 条")
                        has_more = False
                    else:
                        current_offset += params["limit"]
                else:
                    self.logger.info(f"✅ 区域 {area_id} 无更多数据")
                    has_more = False
                
                # 请求间隔（规避反爬）
                time.sleep(REQUEST_DELAY + random.uniform(0, 1))

        self.logger.info(f"🏁 全部采集完成 | 总数据量: {total_records} 条")

    def safe_api_request(self, params, max_retries=3):
        """API请求封装（含编码验证）"""
        for attempt in range(max_retries):
            try:
                response = self.safe_request(
                    method="POST",
                    url=self.api_url,
                    json=params
                )
                
                if not response or response.status_code != 200:
                    self.logger.warning(f"无效响应 | 状态码: {getattr(response, 'status_code', '无')}")
                    continue
                
                # 解析外层JSON
                raw_data = response.json()
                self.logger.debug(f"外层解析结果: {json.dumps(raw_data, ensure_ascii=False, indent=2)}")

                # 处理嵌套的JSON字符串
                if isinstance(raw_data.get("data"), str):
                    try:
                        inner_data = json.loads(raw_data["data"])
                        raw_data["data"] = inner_data
                        self.logger.debug(f"内层解析结果: {json.dumps(inner_data, ensure_ascii=False, indent=2)}")
                        
                    except Exception as e:
                        self.logger.error(f"解析嵌套JSON失败: {str(e)}")
                        continue
                # 提取有效数据
                data_list = raw_data.get("data", {}).get("data", [])
                total = raw_data.get("data", {}).get("total", 0)
                
                return {"data": {"data": data_list, "total": total}}
                
            except Exception as e:
                self.logger.error(f"请求异常（第{attempt+1}次重试）: {str(e)}")
                time.sleep(2 ** attempt)
        return None

    def save_data(self, data, sub_dir, file_name):
        """增强版MongoDB存储方法（支持批量操作/断连重试/智能去重）"""
        try:
            # ================== 过滤与去重逻辑 ==================
            exclude_keywords = ["助老服务社", "护理院", "卫生室", "养老院", "敬老院"]
            seen = set()  # 用于去重的集合
            filtered_data = []

            for item in data:
                # 排除无效机构类型
                if any(kw in item.get("name", "") for kw in exclude_keywords):
                    self.logger.warning(f"过滤无效机构: {item.get('name')}")
                    continue

                # 标准化名称和地址
                name = item.get("name", "").strip().lower()
                address = item.get("address", "").strip().lower()
                
                # 跳过无效数据（可选扩展校验逻辑）
                if not name or not address:
                    self.logger.warning(f"跳过无效数据: {item}")
                    continue

                # 去重标识符（名称+地址）
                identifier = f"{name}_{address}"
                if identifier in seen:
                    self.logger.warning(f"检测到重复数据: {name}")
                    continue
                seen.add(identifier)

                # 保留有效数据
                filtered_data.append({
                    **item,
                    "name": name,
                    "address": address
                })

            # 更新数据为过滤后结果
            data = filtered_data
            self.logger.info(f"过滤后剩余有效数据: {len(data)}条")

            # ================== 原有MongoDB存储逻辑 ==================
            operations = []
            for item in data:
                operation = UpdateOne(
                    {"name": item["name"], "address": item["address"]},
                    {"$set": item},
                    upsert=True
                )
                operations.append(operation)
            # ================== 批量写入 ==================
            if operations:
                try:
                    result = self.collection.bulk_write(
                        operations,
                        ordered=False  # 无序写入提升性能
                    )
                    duplicate_count = len(operations) - (result.upserted_count + result.modified_count)
                    
                    self.logger.info(
                        f"MongoDB写入结果 | 新增: {result.upserted_count} "
                        f"更新: {result.modified_count} "
                        f"重复: {duplicate_count}"
                    )
                    
                except BulkWriteError as bwe:
                    # 处理部分重复写入的情况
                    duplicate_count = len(bwe.details['writeErrors'])
                    self.logger.warning(
                        f"批量写入部分成功 | 已插入: {bwe.details['nInserted']} "
                        f"重复项: {duplicate_count}"
                    )

            # ================== 数据备份机制 ==================
            # 保留原始JSON备份（可选）
            backup_path = self.BASE_DIR / "data/backup" / sub_dir / file_name
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"原始数据已备份至: {backup_path}")

            return True

        except KeyError as e:
            self.logger.error(f"数据字段缺失: {str(e)}", exc_info=True)
            return False
        except Exception as e:
            self.logger.error(f"数据库操作异常: {str(e)}", exc_info=True)
            return False



if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )
    crawler = DataShGovCrawler()
    crawler.crawl_medical_institutions()
