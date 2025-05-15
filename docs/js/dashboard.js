// docs/js/dashboard.js
import { supabase } from './supabase.js'

// 导出需要公开的方法
export async function loadDataMetrics(userId) {
  try {
    const { data: posts } = await supabase
      .from('posts')
      .select('id, content, sentiment, created_at')
      .order('created_at', { ascending: false })

    return {
      metrics: {
        totalPosts: posts?.length || 0,
        positiveRatio: calculatePositiveRatio(posts)
      },
      posts: posts || []
    }
  } catch (error) {
    console.error('数据加载失败:', error);
    return { metrics: {}, posts: [] };
  }
}

// 辅助函数：计算积极评价比例
function calculatePositiveRatio(posts) {
  if (!posts?.length) return 0;
  const positiveCount = posts.filter(p => p.sentiment === 'positive').length;
  return Math.round((positiveCount / posts.length) * 100);
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
        <h3>📊 总评价数</h3>
        <p>${data.metrics.totalPosts}</p>
      </div>
      <div class="metric-card">
        <h3>👍 好评率</h3>
        <p>${data.metrics.positiveRatio}%</p>
      </div>
    </div>
    <div class="post-list">
      ${data.posts.map(post => `
        <div class="post-item">
          <div class="post-content">${post.content}</div>
          <div class="post-meta">
            <span class="sentiment-${post.sentiment}">
              ${post.sentiment === 'positive' ? '积极' : '需改进'}
            </span>
            <span>${new Date(post.created_at).toLocaleDateString()}</span>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}