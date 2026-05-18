#src/crawlers/social_crawlers/zjszyy/bilibili_crawler.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bilibili_crawler.py - 采集B站视频评论，支持用户互动网络分析
Modified: 增加 author_mid, target_mid, reply_to_rpid 字段
"""

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
KEYWORDS = keyword_tool.generate() + ["浙江省中医院", "省中医院", "浙江中医院"]

MAX_VIDEOS_PER_KEYWORD = 10
MAX_COMMENTS_PER_VIDEO = 50
DELAY = 10
REQUEST_TIMEOUT = 15

USE_PROXY = False
PROXY = None

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0'
]

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

video_title_cache = {}
# ==============================================

def get_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Referer': 'https://www.bilibili.com',
        'Accept': 'application/json, text/plain, */*'
    }

def search_videos(keyword, page=1, retry=3):
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
        time.sleep(10)
    return []

# [MODIFIED] 重写 get_video_comments，增加 mid 和目标字段
def get_video_comments(bvid, max_count=50):
    """获取视频评论，返回包含 author_mid, target_mid, reply_to_rpid 的列表"""
    # 获取视频信息（含作者mid）
    info_url = "https://api.bilibili.com/x/web-interface/view"
    params = {'bvid': bvid}
    try:
        resp = requests.get(info_url, headers=get_headers(), params=params, proxies=PROXY, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if data['code'] != 0:
            return []
        owner_mid = data['data']['owner']['mid']          # [NEW] 视频作者UID
        aid = data['data']['aid']
        title = data['data']['title']
        video_title_cache[bvid] = title
    except Exception as e:
        print(f"获取视频信息失败 (bvid={bvid}): {e}")
        return []

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
        data_com = resp.json()
        if data_com['code'] != 0 or 'data' not in data_com or 'replies' not in data_com['data']:
            break

        replies = data_com['data']['replies']
        if not replies:
            break

        for r in replies:
            if len(comments) >= max_count:
                break
            # [NEW] 一级评论：目标为视频作者
            comment = {
                'bvid': bvid,
                'comment_id': r['rpid'],
                'author_mid': r['member']['mid'],       # 评论者UID
                'user_name': r['member']['uname'],
                'content': r['content']['message'],
                'time': r['ctime'],
                'like': r['like'],
                'target_mid': owner_mid,                # 目标：视频作者
                'reply_to_rpid': None
            }
            comments.append(comment)

            # 二级评论（回复）
            if r.get('replies'):
                for sub in r['replies']:
                    if len(comments) >= max_count:
                        break
                    # [NEW] 二级评论：目标为父评论作者
                    sub_comment = {
                        'bvid': bvid,
                        'comment_id': sub['rpid'],
                        'author_mid': sub['member']['mid'],
                        'user_name': sub['member']['uname'],
                        'content': sub['content']['message'],
                        'time': sub['ctime'],
                        'like': sub['like'],
                        'target_mid': r['member']['mid'],  # 目标：父评论作者
                        'reply_to_rpid': r['rpid']
                    }
                    comments.append(sub_comment)
        page += 1
        time.sleep(3)
    return comments

# [MODIFIED] 保存时增加新字段
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
            'author_mid': c['author_mid'],                # [NEW]
            'target_mid': c['target_mid'],                # [NEW]
            'reply_to_rpid': c['reply_to_rpid'],          # [NEW]
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
            'like_count': c['like']
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
    # 确保 Supabase 表中已添加以下字段：
    # ALTER TABLE posts ADD COLUMN IF NOT EXISTS author_mid text;
    # ALTER TABLE posts ADD COLUMN IF NOT EXISTS target_mid text;
    # ALTER TABLE posts ADD COLUMN IF NOT EXISTS reply_to_rpid text;
    main()