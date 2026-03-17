#src/crawlers/social_crawlers/zjszyy/bilibili_crawler.py
import os
import time
import random
import requests
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
from src.crawlers.social_crawlers.zjszyy.keyword_generator import KeywordGenerator

load_dotenv()

# ==================== 配置 ====================
keyword_tool = KeywordGenerator()
# 搜索词：所有完整短语（医院+医生）+ 医院名称
KEYWORDS = keyword_tool.generate() + ["浙江省中医院", "省中医院", "浙江中医院"]

MAX_VIDEOS_PER_KEYWORD = 10      # 每个关键词最多视频数
MAX_COMMENTS_PER_VIDEO = 50      # 每个视频最多评论数
DELAY = 10                       # 请求间隔（秒），增加以降低风控
REQUEST_TIMEOUT = 15              # 请求超时时间

# 关闭代理，直接使用本机 IP
USE_PROXY = False
PROXY = None

# 随机 User-Agent 列表
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0'
]

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 视频信息缓存
video_title_cache = {}
# ==============================================

def get_headers():
    """返回随机User-Agent的请求头"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Referer': 'https://www.bilibili.com',
        'Accept': 'application/json, text/plain, */*'
    }

def search_videos(keyword, page=1, retry=3):
    """搜索视频，带重试机制"""
    search_url = "https://api.bilibili.com/x/web-interface/search/type"
    params = {
        'search_type': 'video',
        'keyword': keyword,
        'page': page,
        'page_size': 30
    }
    for attempt in range(retry):
        try:
            resp = requests.get(
                search_url,
                headers=get_headers(),
                params=params,
                proxies=PROXY,
                timeout=REQUEST_TIMEOUT
            )
            if resp.status_code == 200:
                data = resp.json()
                if data['code'] == 0:
                    return data['data']['result']
                else:
                    print(f"搜索返回错误码: {data['code']}，等待后重试...")
            elif resp.status_code == 412:
                print(f"搜索触发412，第{attempt+1}次重试，等待60秒...")
                time.sleep(60)
                continue
            else:
                print(f"搜索失败: 状态码 {resp.status_code}")
        except requests.exceptions.Timeout:
            print(f"搜索超时，第{attempt+1}次重试...")
        except Exception as e:
            print(f"搜索异常: {e}")
        time.sleep(10)  # 重试间隔
    return []

def get_video_comments(bvid, max_count=50):
    """获取视频评论"""
    # 通过bvid获取aid
    info_url = "https://api.bilibili.com/x/web-interface/view"
    params = {'bvid': bvid}
    try:
        resp = requests.get(info_url, headers=get_headers(), params=params, proxies=PROXY, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if data['code'] != 0:
            return []
        aid = data['data']['aid']
        title = data['data']['title']
        video_title_cache[bvid] = title

        comments = []
        page = 1
        comment_url = "https://api.bilibili.com/x/v2/reply"
        while len(comments) < max_count:
            params = {
                'type': 1,
                'oid': aid,
                'pn': page,
                'ps': 20,
                'sort': 2      # 按热度排序
            }
            resp = requests.get(comment_url, headers=get_headers(), params=params, proxies=PROXY, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                break
            data = resp.json()
            if data['code'] != 0 or 'data' not in data or 'replies' not in data['data']:
                break

            replies = data['data']['replies']
            if not replies:
                break

            for r in replies:
                if len(comments) >= max_count:
                    break
                # 主评论
                comments.append({
                    'bvid': bvid,
                    'comment_id': r['rpid'],
                    'user_name': r['member']['uname'],
                    'content': r['content']['message'],
                    'time': r['ctime'],
                    'like': r['like']
                })
                # 二级评论
                if r.get('replies'):
                    for sub in r['replies']:
                        if len(comments) >= max_count:
                            break
                        comments.append({
                            'bvid': bvid,
                            'comment_id': sub['rpid'],
                            'user_name': sub['member']['uname'],
                            'content': sub['content']['message'],
                            'time': sub['ctime'],
                            'like': sub['like']
                        })
            page += 1
            time.sleep(3)      # 评论翻页间隔
        return comments
    except Exception as e:
        print(f"获取评论失败 (bvid={bvid}): {e}")
        return []

def save_to_supabase(comments):
    if not comments:
        return
    records = []
    for c in comments:
        title = video_title_cache.get(c['bvid'], '')
        detail_url = f"https://www.bilibili.com/video/{c['bvid']}#reply{c['comment_id']}"
        records.append({
            'content': c['content'],
            'author': c['user_name'],
            'raw_post_time': pd.to_datetime(c['time'], unit='s').isoformat(),
            'source': 'bilibili',
            'forum': 'B站视频',
            'title': title,
            'detail_url': detail_url,
            'institution_name': '浙江省中医院',
            'org_code': 'zjszyy',
            'user_id': os.getenv("SUPABASE_USER_UUID_ZJSZYY"),
            'sentiment': None,
            'sentiment_score': None,
            'like_count': c['like']   # 需要表中有此列
        })

    # 按 detail_url 去重
    seen = set()
    unique_records = []
    for rec in records:
        url = rec['detail_url']
        if url not in seen:
            seen.add(url)
            unique_records.append(rec)

    batch_size = 50
    for i in range(0, len(unique_records), batch_size):
        batch = unique_records[i:i+batch_size]
        try:
            supabase.table('posts').upsert(batch, on_conflict='detail_url').execute()
            print(f"✅ 插入 {len(batch)} 条评论")
        except Exception as e:
            print(f"❌ 插入失败: {e}")

def main():
    print(f"共 {len(KEYWORDS)} 个搜索关键词")
    for kw in KEYWORDS:
        print(f"\n🔍 搜索关键词: {kw}")
        videos = search_videos(kw, page=1)
        if not videos:
            print("  没有找到视频")
            continue
        for idx, v in enumerate(videos[:MAX_VIDEOS_PER_KEYWORD]):
            bvid = v.get('bvid', '')
            title = v.get('title', '')
            if bvid and title:
                video_title_cache[bvid] = title
            print(f"  📹 视频 {idx+1}: {title} ({bvid})")
            if not bvid:
                continue
            comments = get_video_comments(bvid, MAX_COMMENTS_PER_VIDEO)
            if comments:
                save_to_supabase(comments)
            time.sleep(DELAY)

if __name__ == "__main__":
    # 确保 Supabase 表中有 like_count 字段
    # 如果没有，请在 Supabase SQL 编辑器中执行：
    # ALTER TABLE posts ADD COLUMN IF NOT EXISTS like_count integer;
    main()