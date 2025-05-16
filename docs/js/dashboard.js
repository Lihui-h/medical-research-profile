// docs/js/dashboard.js
import { supabase } from './supabase.js'

// 初始化配置
const POSTS_PER_PAGE = 20
let currentPage = 1

export async function loadPosts(source = 'all') {
  try {
    const query = supabase
      .from('posts')
      .select('content, sentiment, created_at')
      .order('created_at', { ascending: false })
      .range((currentPage-1)*POSTS_PER_PAGE, currentPage*POSTS_PER_PAGE-1)

    if (source !== 'all') query.eq('source', source)

    const { data: posts } = await query
    return posts || []
  } catch (error) {
    console.error('数据加载失败:', error)
    return []
  }
}

export function renderPosts(posts) {
  const container = document.querySelector('.post-list')
  
  // 清空原有内容
  container.innerHTML = posts.map(post => `
    <div class="post-item ${post.sentiment}">
      <div class="post-content">${post.content}</div>
      <div class="post-meta">
        <span class="sentiment-tag">${
          post.sentiment === 'positive' ? '👍 积极' : '⚠️ 需改进'
        }</span>
        <time>${new Date(post.created_at).toLocaleDateString()}</time>
      </div>
    </div>
  `).join('')

  // 滚动到顶部
  container.scrollTo(0, 0)
}

// 初始化事件监听
export function initDashboardControls() {
  // 来源筛选
  document.getElementById('sourceSelect').addEventListener('change', async (e) => {
    const posts = await loadPosts(e.target.value)
    renderPosts(posts)
  })

  // 滚动加载
  document.querySelector('.scroll-container').addEventListener('scroll', async (e) => {
    const { scrollTop, scrollHeight, clientHeight } = e.target
    if (scrollHeight - scrollTop <= clientHeight * 1.2) {
      currentPage++
      const newPosts = await loadPosts()
      renderPosts([...document.querySelectorAll('.post-item'), ...newPosts])
    }
  })
}