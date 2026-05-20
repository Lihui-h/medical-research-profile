#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bilibili_crawler.py - 采集B站视频评论，支持用户互动网络分析
适配 bilibili-api-python >= 17.x，使用 offset 游标分页
"""

import os
import sys
import asyncio
import re
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# 导入 bilibili-api 核心模块
from bilibili_api import sync, Credential
from bilibili_api import search, video, comment

load_dotenv()

# ---------- 1. 全局认证设置 ----------
credential = Credential(
    sessdata=os.getenv("BILIBILI_SESSDATA"),
    bili_jct=os.getenv("BILIBILI_JCT"),
    buvid3=os.getenv("BILIBILI_BUVID3")
)
# 将 credential 设置为全局默认（官方推荐方式）
import bilibili_api
bilibili_api.credential = credential

# ---------- 2. 数据保存到 Supabase ----------
def save_to_supabase(comments):
    """将评论数据批量 upsert 到 posts 表"""
    if not comments:
        return
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    supabase_client: Client = create_client(supabase_url, supabase_key)

    records = []
    for c in comments:
        raw_time = datetime.fromtimestamp(c['time']).isoformat()
        records.append({
            'content': c['content'],
            'author': c.get('user_name', '未知用户'),
            'author_mid': str(c['author_mid']),
            'target_mid': str(c['target_mid']) if c.get('target_mid') else None,
            'reply_to_rpid': str(c['reply_to_rpid']) if c.get('reply_to_rpid') else None,
            'raw_post_time': raw_time,
            'source': 'bilibili',
            'forum': 'B站视频',
            'title': c.get('title', ''),
            'detail_url': c.get('detail_url', ''),
            'institution_name': '浙江省中医院',
            'org_code': 'zjszyy',
            'user_id': os.getenv("SUPABASE_USER_UUID_ZJSZYY"),
            'sentiment': None,
            'sentiment_score': None,
            'like_count': c.get('like', 0)
        })

    # 去重（基于 detail_url + author_mid + reply_to_rpid）
    seen = set()
    unique_records = []
    for rec in records:
        key = f"{rec['detail_url']}_{rec['author_mid']}_{rec['reply_to_rpid']}"
        if key not in seen:
            seen.add(key)
            unique_records.append(rec)

    # 批量插入
    batch_size = 50
    for i in range(0, len(unique_records), batch_size):
        batch = unique_records[i:i+batch_size]
        try:
            supabase_client.table('posts').upsert(batch, on_conflict='detail_url').execute()
            print(f"✅ 插入 {len(batch)} 条评论")
        except Exception as e:
            print(f"❌ 插入失败: {e}")

# ---------- 3. 异步获取单个视频的所有评论（使用 offset 游标分页）----------
async def fetch_comments_for_bvid(bvid: str, video_title: str, max_comments: int = 50):
    """使用最新的 offset 游标分页方式获取一个视频的评论和回复"""
    v_obj = video.Video(bvid=bvid, credential=credential)
    try:
        # 获取视频信息（包含 aid 和 UP 主 mid）
        video_info = await v_obj.get_info()
        owner_mid = video_info['owner']['mid']
        aid = video_info['aid']

        all_comments = []
        offset = ""  # 分页游标，初始为空字符串
        while len(all_comments) < max_comments:
            try:
                # 调用新版接口，使用 offset 进行分页
                comment_page = await comment.get_comments_lazy(
                    oid=aid,
                    type_=comment.CommentResourceType.VIDEO,
                    offset=offset,
                    credential=credential
                )
            except Exception as e:
                print(f"    获取评论页失败: {e}")
                break

            replies = comment_page.get('replies', [])
            if not replies:
                break

            # 解析当前页的评论和回复
            for root_reply in replies:
                if len(all_comments) >= max_comments:
                    break
                # 一级评论（主楼）
                all_comments.append({
                    'bvid': bvid,
                    'comment_id': root_reply['rpid'],
                    'author_mid': root_reply['mid'],
                    'user_name': root_reply['member']['uname'],
                    'content': root_reply['content']['message'],
                    'time': root_reply['ctime'],
                    'like': root_reply['like'],
                    'target_mid': owner_mid,  # 一级评论目标是UP主
                    'reply_to_rpid': None,
                    'title': video_title,
                    'detail_url': f"https://www.bilibili.com/video/{bvid}#reply{root_reply['rpid']}"
                })
                # 二级评论（楼中楼回复）
                if root_reply.get('replies'):
                    for sub_reply in root_reply['replies']:
                        if len(all_comments) >= max_comments:
                            break
                        all_comments.append({
                            'bvid': bvid,
                            'comment_id': sub_reply['rpid'],
                            'author_mid': sub_reply['mid'],
                            'user_name': sub_reply['member']['uname'],
                            'content': sub_reply['content']['message'],
                            'time': sub_reply['ctime'],
                            'like': sub_reply['like'],
                            'target_mid': root_reply['mid'],  # 回复的目标是父评论作者
                            'reply_to_rpid': root_reply['rpid'],  # 记录父评论ID
                            'title': video_title,
                            'detail_url': f"https://www.bilibili.com/video/{bvid}#reply{sub_reply['rpid']}"
                        })

            # 获取下一页游标
            cursor = comment_page.get('cursor', {})
            # 注意：返回的 cursor 中可能包含 'pagination_reply' 字段，其内可能有 'next_offset'
            pagination_reply = cursor.get('pagination_reply', {})
            next_offset = pagination_reply.get('next_offset')
            if not next_offset:
                break  # 没有下一页了
            offset = next_offset  # 更新游标
            await asyncio.sleep(1)  # 礼貌性延迟

        print(f"    视频 {bvid} 共获取 {len(all_comments)} 条评论/回复")
        return all_comments
    except Exception as e:
        print(f"视频 {bvid} 处理出错: {e}")
        return []

# ---------- 4. 主爬虫流程 ----------
async def crawl():
    # 导入关键词生成器（确保路径正确）
    from src.crawlers.social_crawlers.zjszyy.keyword_generator import KeywordGenerator
    keyword_tool = KeywordGenerator()
    KEYWORDS = keyword_tool.generate() + ["浙江省中医院", "省中医院", "浙江中医院"]

    for kw in KEYWORDS:
        print(f"\n[搜索] 关键词: {kw}")
        try:
            # 搜索视频（不需要显式传递 credential，因为已全局设置）
            search_result = await search.search_by_type(
                kw,
                search_type=search.SearchObjectType.VIDEO,
                page=1
            )
        except Exception as e:
            print(f"[错误] 搜索失败: {e}")
            continue

        videos = search_result.get('result', [])[:10]   # 每个关键词最多处理10个视频
        if not videos:
            print("未找到视频")
            continue

        for idx, v in enumerate(videos):
            bvid = v.get('bvid')
            title = v.get('title', '无标题')
            # 清理标题中的 HTML 标签
            title_clean = re.sub(r'<[^>]+>', '', title)
            print(f"  视频 {idx+1}: {title_clean} ({bvid})")
            if not bvid:
                continue
            comments = await fetch_comments_for_bvid(bvid, title_clean)
            if comments:
                save_to_supabase(comments)
            await asyncio.sleep(3)   # 视频间延迟

def main():
    """同步入口"""
    sync(crawl())

if __name__ == "__main__":
    # 确保 Supabase 的 posts 表已经包含以下字段（如果没有，请先在 SQL 编辑器中执行）：
    # ALTER TABLE posts ADD COLUMN IF NOT EXISTS author_mid text;
    # ALTER TABLE posts ADD COLUMN IF NOT EXISTS target_mid text;
    # ALTER TABLE posts ADD COLUMN IF NOT EXISTS reply_to_rpid text;
    main()