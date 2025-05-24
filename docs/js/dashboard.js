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
      .select('id, content, sentiment, sentiment_score, raw_post_time')
      .order('raw_post_time', { ascending: false })
    
    // 新增稳定性计算
    const stabilityAnalyzer = new StabilityAnalyzer();
    const stabilityData = stabilityAnalyzer.simulate(
      posts.map(p => p.sentiment_score)
    );

    // 新增：微分方程模拟生成相空间数据
    const phaseData = simulatePhaseTrajectory(
      posts.map(p => p.sentiment_score),
      posts.map(p => p.raw_post_time)
    );

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

  // 添加稳定性图表
  renderStabilityChart('trend-chart', {
    dates: data.posts.map(p => p.created_at),
    scores: data.posts.map(p => p.sentiment_score),
    stability: data.stability
  });

  // 初始化相轨迹
  const portrait = new PhasePortrait('phase-canvas', data.phaseData);
  portrait.animate();

  // 新增词云渲染
  renderWordCloud('wordcloud-canvas', data.wordCloud);
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

// 微分方程模拟器
function simulatePhaseTrajectory(scores, timestamps) {
  const states = [];
  let S = 0.5, I = 0.3, N = 0.2; // 初始状态
  
  scores.forEach((score, i) => {
    // 根据实际模型参数计算微分方程
    const dS = 0.2*N + 0.1*I - 0.15*S;
    const dI = 0.3*N + 0.25*S - 0.18*I;
    const dN = 0.15*S + 0.1*I - 0.3*N;
    
    // 更新状态
    S += dS * timeStep(timestamps[i]);
    I += dI * timeStep(timestamps[i]);
    N += dN * timeStep(timestamps[i]);

    states.push({ S, I, N, dI });
  });
  
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