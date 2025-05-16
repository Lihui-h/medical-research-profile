// docs/js/dashboard.js
import { supabase } from './supabase.js'
import Chart from 'https://cdn.skypack.dev/chart.js@3.7.0';
import WordCloud from 'https://cdn.skypack.dev/wordcloud@1.2.2';

// 全局图表实例引用
let trendChart = null;
let wordCloudInstance = null;

export async function loadDataMetrics(filterSource = 'all') {
  try {
    let query = supabase
      .from('posts')
      .select('id, content, sentiment, created_at, source')
      .order('created_at', { ascending: false });

    // 添加数据源过滤
    if (filterSource !== 'all') {
      query = query.eq('source', filterSource);
    }

    const { data: posts, error } = await query;

    if (error) throw error;

    return {
      metrics: {
        totalPosts: posts?.length || 0,
        positiveRatio: calculatePositiveRatio(posts),
        sources: countDataSources(posts)
      },
      posts: posts || [],
      trends: processTrendData(posts)
    };
  } catch (error) {
    console.error('数据加载失败:', error);
    return { metrics: {}, posts: [], trends: [] };
  }
}

export function renderDashboard(containerId, data) {
  const container = document.getElementById(containerId);
  if (!container) return;

  // 清空旧图表
  if (trendChart) trendChart.destroy();
  if (wordCloudInstance) wordCloudInstance.dispose();

  container.innerHTML = `
    <div class="metric-grid">
      <div class="metric-card">
        <h3>📊 总评价数</h3>
        <p>${data.metrics.totalPosts}</p>
        <div class="source-tags">
          ${Object.entries(data.metrics.sources).map(([source, count]) => `
            <span class="source-tag" data-source="${source}">${source}: ${count}</span>
          `).join('')}
        </div>
      </div>
      <div class="metric-card">
        <h3>👍 好评率</h3>
        <p>${data.metrics.positiveRatio}%</p>
      </div>
    </div>

    <div class="data-container">
      <div class="post-list">
        ${data.posts.map(post => `
          <div class="post-item">
            <div class="post-content">${post.content}</div>
            <div class="post-meta">
              <span class="sentiment-${post.sentiment}">
                ${post.sentiment === 'positive' ? '积极' : '需改进'}
              </span>
              <span class="post-source">来源：${post.source || '未知'}</span>
              <span>${new Date(post.created_at).toLocaleDateString()}</span>
            </div>
          </div>
        `).join('')}
      </div>

      <div id="trend-analysis" class="hidden">
        <canvas id="trend-chart"></canvas>
      </div>

      <div id="wordcloud" class="hidden">
        <canvas id="wordcloud-canvas"></canvas>
      </div>
    </div>
  `;

  // 初始化图表
  renderTrendChart(data.trends);
  renderWordCloud(data.posts);
  initEventListeners();
}

// 辅助函数
function calculatePositiveRatio(posts) {
  if (!posts?.length) return 0;
  const positiveCount = posts.filter(p => p.sentiment === 'positive').length;
  return Math.round((positiveCount / posts.length) * 100);
}

function countDataSources(posts) {
  return posts?.reduce((acc, { source }) => {
    acc[source] = (acc[source] || 0) + 1;
    return acc;
  }, {}) || {};
}

function processTrendData(posts) {
  const dateMap = posts?.reduce((acc, { created_at }) => {
    const date = new Date(created_at).toISOString().split('T')[0];
    acc[date] = (acc[date] || 0) + 1;
    return acc;
  }, {});

  return Object.entries(dateMap || {}).map(([date, count]) => ({
    date,
    count
  }));
}

function renderTrendChart(trendData) {
  const ctx = document.getElementById('trend-chart');
  if (!ctx) return;

  trendChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: trendData.map(d => d.date),
      datasets: [{
        label: '评价数量趋势',
        data: trendData.map(d => d.count),
        borderColor: '#4CAF50',
        tension: 0.1
      }]
    }
  });
}

function renderWordCloud(posts) {
  const content = posts?.map(p => p.content).join(' ') || '';
  const words = extractKeywords(content);
  
  wordCloudInstance = WordCloud(document.getElementById('wordcloud-canvas'), { 
    list: words,
    backgroundColor: '#f8f9fa',
    weightFactor: 10,
    color: '#2196F3'
  });
}

function extractKeywords(text, topN = 20) {
  const wordMap = text.toLowerCase().split(/[\s,.!?]+/).reduce((acc, word) => {
    if (word.length > 1) acc[word] = (acc[word] || 0) + 1;
    return acc;
  }, {});

  return Object.entries(wordMap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, topN)
    .map(([text, weight]) => [text, weight]);
}

function initEventListeners() {
  // 导航切换
  document.querySelectorAll('.source-tab, .analysis-tab, .wordcloud-tab').forEach(tab => {
    tab.addEventListener('click', async (e) => {
      e.preventDefault();
      const target = e.target.dataset.source || e.target.classList[0];

      // 切换内容显示
      document.querySelectorAll('#dashboard-content, #trend-analysis, #wordcloud')
        .forEach(el => el.classList.add('hidden'));
      
      if (target === 'baidu') {
        const data = await loadDataMetrics('baidu_tieba');
        renderDashboard('dashboard-content', data);
      } else {
        document.getElementById(target).classList.remove('hidden');
      }
    });
  });
}