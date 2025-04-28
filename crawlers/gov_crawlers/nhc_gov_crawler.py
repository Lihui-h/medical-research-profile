# src/crawlers/gov_crawlers/nhc_gov_crawler.py
# -*- coding: utf-8 -*-
import os
import sys
import random
import time
import pdfplumber
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
from typing import List, Dict
from .base_gov_crawler import BaseGovCrawler

class NHCCrawler(BaseGovCrawler):
    """国家卫健委官网数据采集爬虫（编码问题终极修复版）"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "http://www.nhc.gov.cn"
        self.search_keywords = os.getenv("NHC_SEARCH_KEYWORDS", "孕产妇保健 医院评价").split()
        self.pdf_links = []
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 初始化时验证编码
        self.logger.debug("系统默认编码: %s", sys.getdefaultencoding())
        self.logger.debug("文件系统编码: %s", sys.getfilesystemencoding())

    def crawl_annual_reports(self, max_pdf: int = 3) -> List[Dict]:
        """主采集流程"""
        results = []
        try:
            self.logger.info("开始采集流程 | 最大PDF数量=%d", max_pdf)
            
            # 第一阶段：搜索报告
            search_success = self._search_reports()
            if not search_success:
                self.logger.error("报告搜索阶段失败")
                return results
                
            # 第二阶段：处理PDF
            for idx, pdf_url in enumerate(self.pdf_links[:max_pdf]):
                self.logger.info("正在处理第%d个PDF | URL=%s", idx+1, pdf_url)
                if pdf_data := self._process_pdf(pdf_url):
                    results.append(pdf_data)
                    self.random_delay(2, 5)  # 使用基类的随机延迟方法
                    
        except Exception as e:
            self.logger.exception("主流程发生未捕获异常")
        finally:
            self.logger.info("采集流程结束 | 获取报告数量=%d", len(results))
            return results

    def _search_reports(self) -> bool:
        """搜索报告（强化编码处理）"""
        try:
            # 生成双重编码关键词
            keyword = random.choice(self.search_keywords)
            self.logger.debug("原始关键词: %s", keyword)
            
            # 第一层编码：UTF-8转字节
            stage1 = keyword.encode("utf-8", errors="replace")
            # 第二层编码：URL百分号编码
            encoded_keyword = quote(stage1.decode("latin-1"))
            
            search_url = f"{self.base_url}/s?q={encoded_keyword}"
            self.logger.debug("编码后URL: %s", search_url)
            
            # 构建强化请求头
            headers = self.generate_headers()
            headers.update({
                "Accept-Charset": "utf-8",
                "Content-Type": "application/x-www-form-urlencoded; charset=utf-8"
            })
            
            # 发送请求
            response = self.safe_request("GET", search_url, headers=headers)
            if not response:
                return False
                
            # 强制设置响应编码
            response.encoding = "utf-8"  # 覆盖requests自动检测
            
            # 解析结果
            soup = BeautifulSoup(response.text, "html.parser")
            pdf_elements = soup.select('a[href$=".pdf"]')
            self.pdf_links = [
                urljoin(self.base_url, a["href"]) 
                for a in pdf_elements 
                if "妇幼" in a.text
            ]
            self.logger.info("报告搜索成功 | 找到PDF数量=%d", len(self.pdf_links))
            return True
            
        except Exception as e:
            self.logger.error("报告搜索失败 | 错误信息=%s", str(e))
            return False

    def _process_pdf(self, pdf_url: str) -> Dict:
        """处理单个PDF文件"""
        try:
            # 下载PDF
            file_path = self._download_pdf(pdf_url)
            if not file_path:
                return None
                
            # 解析文本
            text_content = self._parse_pdf(file_path)
            
            return {
                "source_url": pdf_url,
                "local_path": str(file_path),
                "content": text_content[:5000] + "..."  # 截断处理
            }
        except Exception as e:
            self.logger.error("PDF处理失败 | URL=%s | 错误=%s", pdf_url, str(e))
            return None

    def _download_pdf(self, url: str) -> Path:
        """下载PDF文件"""
        try:
            # 发送请求
            response = self.safe_request("GET", url)
            if not response or not response.content:
                self.logger.warning("空响应内容 | URL=%s", url)
                return None
                
            # 生成保存路径
            save_dir = self.BASE_DIR / "data/raw/nhc_reports"
            save_dir.mkdir(parents=True, exist_ok=True)
            file_name = f"nhc_{os.path.basename(url)}"
            file_path = save_dir / file_name
            
            # 写入文件
            with open(file_path, "wb") as f:
                f.write(response.content)
            self.logger.info("PDF下载成功 | 路径=%s", file_path)
            return file_path
            
        except Exception as e:
            self.logger.error("PDF下载失败 | URL=%s | 错误=%s", url, str(e))
            return None

    def _parse_pdf(self, file_path: Path) -> str:
        """解析PDF文本（强化编码处理）"""
        text = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # 使用宽松解析参数
                    page_text = page.extract_text(
                        x_tolerance=2, 
                        y_tolerance=2,
                        keep_blank_chars=True
                    )
                    if page_text:
                        # 编码清理
                        clean_text = page_text.encode("utf-8", errors="replace").decode("utf-8")
                        text.append(clean_text)
                        
            # 保存文本文件
            txt_path = file_path.with_suffix(".txt")
            with open(txt_path, "w", encoding="utf-8", errors="replace") as f:
                f.write("\n".join(text))
                
            return "\n".join(text)
            
        except pdfplumber.PDFSyntaxError:
            self.logger.error("PDF解析失败 | 文件可能损坏 | 路径=%s", file_path)
            return ""
        except Exception as e:
            self.logger.error("PDF解析异常 | 路径=%s | 错误=%s", file_path, str(e))
            return ""

if __name__ == "__main__":
    # 初始化日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("nhc_crawler.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    
    # 执行测试
    print("=== 卫健委爬虫测试开始 ===")
    crawler = NHCCrawler()
    
    # 验证代理
    if not crawler.validate_proxy():
        print("代理验证失败，请检查配置")
        exit(1)
        
    # 执行采集
    reports = crawler.crawl_annual_reports(max_pdf=2)
    print(f"\n=== 测试完成 ===")
    print(f"成功获取报告数量: {len(reports)}")
    if reports:
        print("首个报告摘要:")
        print(reports[0]["content"][:200] + "...")