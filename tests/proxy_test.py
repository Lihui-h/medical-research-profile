# proxy_test.py
import requests
import logging
import time
import random

logging.basicConfig(level=logging.DEBUG)

# 代理配置
proxies = {
    'http': 'http://customer-ContagioScope_medtrust_CsM7j-cc-cn:00fk51uN_csm@pr.oxylabs.io:7777'
            '?country=cn'
            '&session=rotate'
            '&prerender=false',
    'https': 'http://customer-ContagioScope_medtrust_CsM7j-cc-cn:00fk51uN_csm@pr.oxylabs.io:7777'
            '?country=cn'
            '&session=rotate'
            '&prerender=false'
}

# 请求头配置
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Referer": "https://www.baidu.com/"
}

session = requests.Session()
session.proxies = proxies
session.headers = headers

try:
    # 基础代理测试
    print("=== 代理基础测试 ===")
    res = session.get('http://httpbin.org/ip', timeout=10)
    print(f"代理IP: {res.text}")

    # 目标网站测试
    print("\n=== 目标网站测试 ===")
    time.sleep(random.uniform(2, 5))
    response = session.get('http://www.nhc.gov.cn/wjw/zcjd/list.shtml', timeout=15)
    print(f"状态码: {response.status_code}")
    print(f"内容长度: {len(response.text)}")

except Exception as e:
    print(f"错误详情: {str(e)}")