// 新增js/dashboard.js
async function loadDataMetrics(userId) {
    // 获取基础指标
    const { data: metrics } = await supabase
      .from('org_metrics')
      .select('posts, keywords')
      .eq('id', userId)
      .single()
  
    // 获取帖子列表
    const { data: posts } = await supabase
      .from('posts')
      .select('id, content, sentiment, created_at')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
  
    renderDashboard({
      metrics: metrics || { posts: [], keywords: [] },
      posts: posts || []
    })
  }
  
  function renderDashboard(data) {
    const container = document.getElementById('dashboard-content')
    
    // 清空旧内容
    container.innerHTML = ''
  
    // 构建数据卡片
    const cardsHtml = `
      <div class="metric-card">
        <h3>📝 帖子总量</h3>
        <p>${data.metrics.posts.length}</p>
      </div>
      <div class="metric-card">
        <h3>🔑 关键词数量</h3>
        <p>${data.metrics.keywords.length}</p>
      </div>
    `
    
    // 构建帖子列表
    const postsHtml = data.posts.map(post => `
      <div class="post-item">
        <div class="post-content">${post.content.slice(0, 50)}...</div>
        <div class="post-meta">
          <span class="sentiment-${post.sentiment}">${post.sentiment}</span>
          <span>${new Date(post.created_at).toLocaleDateString()}</span>
        </div>
      </div>
    `).join('')
  
    container.innerHTML = `
      <div class="metric-grid">${cardsHtml}</div>
      <div class="post-list">${postsHtml}</div>
    `
  }