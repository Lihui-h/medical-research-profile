// docs/js/dashboard.js
import { supabase } from './supabase.js'

// 导出需要公开的方法
export async function loadDataMetrics(userId) {
  try {
    const { data: metrics } = await supabase
      .from('org_metrics')
      .select('posts, keywords')
      .eq('id', userId)
      .single()

    const { data: posts } = await supabase
      .from('posts')
      .select('id, content, sentiment, created_at')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })

    return {
      metrics: metrics || { posts: [], keywords: [] },
      posts: posts || []
    }
  } catch (error) {
    console.error('数据加载失败:', error)
    return { metrics: { posts: [], keywords: [] }, posts: [] }
  }
}

export function renderDashboard(containerId, data) {
  const container = document.getElementById(containerId)
  
  // 安全校验
  if (!container) {
    console.error('目标容器不存在')
    return
  }

  container.innerHTML = `
    <div class="metric-grid">
      <div class="metric-card">
        <h3>📝 帖子总量</h3>
        <p>${data.metrics.posts.length}</p>
      </div>
      <div class="metric-card">
        <h3>🔑 关键词数量</h3>
        <p>${data.metrics.keywords.length}</p>
      </div>
    </div>
    <div class="post-list">
      ${data.posts.map(post => `
        <div class="post-item">
          <div class="post-content">${post.content.slice(0, 50)}...</div>
          <div class="post-meta">
            <span class="sentiment-${post.sentiment}">${post.sentiment}</span>
            <span>${new Date(post.created_at).toLocaleDateString()}</span>
          </div>
        </div>
      `).join('')}
    </div>
  `
}