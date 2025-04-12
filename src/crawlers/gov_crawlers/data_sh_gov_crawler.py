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
        self.api_url = "https://data.sh.gov.cn/interface/AG9102015009/14661"
        self.proxy_enabled = False  # 强制禁用代理
        # 初始化请求参数（双重编码保护）
        self.required_params = {
            "area_id": str(os.getenv("DEFAULT_AREA_ID", "20")),
            "limit": 200,
            "offset": 0
        }
        # 详细类型检查
        self.logger.debug(f"参数类型检查 - area_id: {type(self.required_params['area_id'])}")

    def crawl_medical_institutions(self):
        """主采集流程"""
        total_records = 0
        current_offset = 0
        MAX_PAGES = 20  # 防止无限循环
        
        while current_offset < MAX_PAGES * self.required_params["limit"]:
            params = {**self.required_params, "offset": current_offset}
            self.logger.debug(f"当前分页参数: offset={current_offset}")
            
            result = self.safe_api_request(params)
            if not result or "data" not in result:
                self.logger.error("接口未返回有效数据")
                break
                
            data = result["data"].get("data", [])
            total = result["data"].get("total", 0)
            
            # 保存数据
            if self.save_data(data, "gov_reports", f"medical_{datetime.now().strftime('%Y%m%d')}.json"):
                total_records += len(data)
            
            # 分页终止条件
            if total == 0:  # 接口未正确返回total时强制分页
                current_offset += self.required_params["limit"]
            else:
                if current_offset + self.required_params["limit"] >= total:
                    self.logger.debug(f"分页终止: current_offset={current_offset}, total={total}")
                    break
                current_offset += self.required_params["limit"]
            
            time.sleep(random.uniform(1, 2))  # 随机延迟
            
        self.logger.info(f"采集完成 | 共获取 {total_records} 条数据")

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
            # ================== 初始化MongoDB连接 ==================
            # 从环境变量获取配置（在.env中添加）
            mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
            db_name = os.getenv("MONGODB_DB", "medical_db")
            collection_name = os.getenv("MONGODB_COLLECTION", "hospitals")
            
            # 创建具备重试机制的连接
            client = MongoClient(
                mongodb_uri,
                serverSelectionTimeoutMS=5000,  # 5秒连接超时
                socketTimeoutMS=30000,          # 30秒操作超时
                retryWrites=True                # 启用写入重试
            )
            
            # 验证连接状态
            try:
                client.admin.command('ping')
                self.logger.debug("成功连接到MongoDB服务器")
            except ConnectionFailure:
                self.logger.error("无法连接MongoDB服务器")
                return False

            db = client[db_name]
            collection = db[collection_name]

            # ================== 索引管理 ==================
            # 创建唯一复合索引（仅首次运行时创建）
            index_name = "name_address_unique"
            if index_name not in collection.index_information():
                collection.create_index(
                    [("name", 1), ("address", 1)],
                    unique=True,
                    name=index_name,
                    background=True  # 后台构建不影响服务
                )
                self.logger.info("已创建唯一性索引: name + address")

            # ================== 数据预处理 ==================
            operations = []
            duplicate_count = 0
            valid_count = 0

            for item in data:
                # 字段标准化处理
                name = item.get("name", "").strip().lower()
                address = item.get("address", "").strip().lower()
                
                # 跳过无效数据（可选扩展校验逻辑）
                if not name or not address:
                    self.logger.warning(f"跳过无效数据: {item}")
                    continue

                # 构造更新操作（upsert模式）
                operation = UpdateOne(
                    {"name": name, "address": address},
                    {"$set": {**item, "name": name, "address": address}},  # 标准化存储
                    upsert=True
                )
                operations.append(operation)
                valid_count += 1

            # ================== 批量写入 ==================
            if operations:
                try:
                    result = collection.bulk_write(
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
        finally:
            # 确保关闭连接
            if 'client' in locals():
                client.close()



if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )
    crawler = DataShGovCrawler()
    crawler.crawl_medical_institutions()
