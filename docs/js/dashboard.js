// docs/js/dashboard.js
import { supabase } from './supabase.js';
import { StabilityAnalyzer } from './stability.js';
import { renderWordCloud } from './wordcloud.js';
import { PhasePortrait } from './phase-portrait.js';

// 导出需要公开的方法
export async function loadDataMetrics(userId) {
  try {
    const { data: posts } = await supabase
      .from('posts')
      .select('id, content, title, forum, sentiment, sentiment_score, raw_post_time')
      .order('raw_post_time', { ascending: false })
    
    // 新增稳定性计算
    const stabilityAnalyzer = new StabilityAnalyzer();
    const stabilityData = stabilityAnalyzer.simulate(
      posts.map(p => p.sentiment_score)
    );

    // 新增：微分方程模拟生成相空间数据
    const phaseData = simulatePhaseTrajectory(posts);

    // 新增词频统计
    const wordCounts = calculateWordFrequency(posts);

    return {
      metrics: {
        totalPosts: posts?.length || 0,
        positiveRatio: calculatePositiveRatio(posts)
      },
      posts: posts || [],
      stability: stabilityData,
      phaseData: phaseData,
      wordCloud: wordCounts
    };
  } catch (error) {
    console.error('数据加载失败:', error);
    return { metrics: {}, posts: [], stability: [], phaseData: [], wordCloud: [] };
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
    <div class="post-list">
      ${data.posts.map(post => `
        <div class="post-item">
          <div class="post-header">
            <h4 class="post-title">${post.title || '无标题'}</h4>
            <span class="post-forum">来自：${post.forum || '未知贴吧'}</span>
          </div>
          <div class="post-content">${post.content}</div>
          <div class="post-meta">
            <span class="sentiment-tag ${post.sentiment}">
              ${getSentimentLabel(post.sentiment)}
            </span>
            <span class="post-time">
              ${new Date(post.raw_post_time).toLocaleDateString()}
            </span>
          </div>
        </div>
      `).join('')}
    </div>
  `;

  // 添加稳定性图表
  renderStabilityChart('trend-chart', {
    dates: data.posts.map(p => p.raw_post_time),
    scores: data.posts.map(p => p.sentiment_score),
    stability: data.stability
  });

  // 初始化相轨迹
  const portrait = new PhasePortrait('phase-canvas', data.phaseData);
  portrait.animate();

  // 新增词云渲染
  renderWordCloud('wordcloud-canvas', data.wordCloud);
}

// 情感标签文字映射
function getSentimentLabel(sentiment) {
  return {
    positive: '👍 积极',
    neutral: '🔍 中立',
    negative: '⚠️ 负面'
  }[sentiment] || '❓ 未知';
}

function renderStabilityChart(containerId, data) {
  const ctx = document.createElement('canvas');
  document.getElementById(containerId).appendChild(ctx);

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.dates,
      datasets: [
        {
          label: '情感分数',
          data: data.scores,
          borderColor: '#4CAF50',
          tension: 0.4,
          yAxisID: 'y1'
        },
        {
          label: '稳定性指数',
          data: data.stability.map(s => s.stability),
          borderColor: '#FF9800',
          tension: 0.4,
          yAxisID: 'y2'
        }
      ]
    },
    options: {
      scales: {
        y1: {
          type: 'linear',
          position: 'left',
          min: -10,
          max: 10
        },
        y2: {
          type: 'linear',
          position: 'right',
          min: -100,
          max: 100
        }
      },
      plugins: {
        annotation: {
          annotations: {
            stableBox: {
              type: 'box',
              yMin: -3,
              yMax: 3,
              backgroundColor: 'rgba(33,150,243,0.1)'
            }
          }
        }
      }
    }
  });
}

const MODEL_PARAMS = {
  beta_N: 0.03,  // 中立人群被负面影响率
  beta_I: 0.02,  // 积极人群被负面影响率
  gamma: 0.02,   // 负面转中立率
  delta: 0.02,   // 负面直接恢复率
  alpha: 0.05,   // 中立转积极率
  rho: 0.03,     // 负面转积极率
  epsilon: 0.02, // 积极转中立率
  mu: 0.01       // 积极直接恢复率
};

// 微分方程模拟器
function simulatePhaseTrajectory(posts) {
  const C = 100; // 总人口基数（假设总帖子数为100）
  let S = posts.filter(p => p.sentiment === 'negative').length; // 初始负面人数
  let I = posts.filter(p => p.sentiment === 'positive').length; // 初始积极人数
  let N = C - S - I; // 初始中立人数

  const states = [];
  const dt = 1; // 时间步长（天）

  // 模拟40天动态（可根据数据量调整）
  for (let day = 0; day < 40; day++) {
    // 微分方程计算（简化模型）
    const dS = MODEL_PARAMS.beta_N * N + MODEL_PARAMS.beta_I * I 
             - (MODEL_PARAMS.gamma + MODEL_PARAMS.delta) * S
             - 0.001 * S * I; // 非线性耦合项
    const dI = MODEL_PARAMS.alpha * N + MODEL_PARAMS.rho * S 
             - (MODEL_PARAMS.epsilon + MODEL_PARAMS.mu) * I
             + 0.001 * S * I; // 非线性耦合项
    const dN = -dS - dI; // 根据守恒关系 S + I + N = C

    // 更新状态（保证非负）
    S = Math.max(0, S + dS * dt);
    I = Math.max(0, I + dI * dt);
    N = Math.max(0, C - S - I);

    states.push({ S, I });
  };
  
  return states;
}

// 词频统计函数
function calculateWordFrequency(posts) {
  const words = posts.flatMap(p => 
    p.content.split(/[\s\n，。；！？]+/).filter(w => w.length > 1)
  );
  
  const wordMap = words.reduce((map, word) => {
    map.set(word, (map.get(word) || 0) + 1);
    return map;
  }, new Map());

  return Array.from(wordMap, ([word, count]) => ({ word, count }));
}