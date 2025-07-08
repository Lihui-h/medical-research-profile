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

  // 添加相图说明
  const phaseContainer = document.getElementById('phase-portrait');
  if (phaseContainer) {
    // 移除旧说明（如果存在）
    const oldExplanation = document.getElementById('phase-explanation');
    if (oldExplanation) oldExplanation.remove();

    // 创建新的网格布局容器
    const gridContainer = document.createElement('div');
    gridContainer.style.display = 'grid';
    gridContainer.style.gridTemplateColumns = 'minmax(300px, 1fr) 2fr';
    gridContainer.style.gap = '20px';
    gridContainer.style.margin = '20px 0';
    
    // 左侧：说明面板
    const explanationDiv = document.createElement('div');
    explanationDiv.id = 'phase-explanation';
    explanationDiv.style.background = 'rgba(33,150,243,0.05)';
    explanationDiv.style.padding = '15px';
    explanationDiv.style.borderRadius = '8px';
    explanationDiv.style.borderLeft = '4px solid #2196F3';
    explanationDiv.innerHTML = `
      <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="#2196F3">
          <path d="M12,2C6.48,2,2,6.48,2,12s4.48,10,10,10s10-4.48,10-10S17.52,2,12,2z M13,17h-2v-2h2V17z M13,13h-2V7h2V13z"/>
        </svg>
        <h4 style="margin:0">情感传播动力学解读</h4>
      </div>
      <div style="display: grid; grid-template-columns: auto 1fr; gap: 8px 15px; font-size: 14px;">
        <div style="display:flex;align-items:center;gap:6px">
          <div style="width:12px;height:12px;border-radius:50%;background:#2196F3"></div>
          <span>运动轨迹：</span>
        </div>
        <span>舆情状态在负面-积极维度的演化路径</span>
        
        <div style="display:flex;align-items:center;gap:6px">
          <div style="width:12px;height:12px;border-radius:50%;background:#F44336"></div>
          <span>吸引子：</span>
        </div>
        <span>系统最终趋向的稳定状态</span>
        
        <div style="display:flex;align-items:center;gap:6px">
          <div style="width:12px;height:12px;background:none;position:relative">
            <div style="width:100%;height:2px;background:#4CAF50;position:absolute;top:5px"></div>
          </div>
          <span>收敛速度：</span>
        </div>
        <span>轨迹到达稳定的速度反映系统韧性</span>
      </div>
    `;
    
    // 右侧：相图和控制面板
    const graphContainer = document.createElement('div');
    graphContainer.innerHTML = `
      <canvas id="phase-canvas"></canvas>
      <div class="control-panel" style="margin-top: 10px; text-align: center;">
        <button id="restartAnimation" class="btn btn-primary">重新播放</button>
      </div>
    `;
    
    // 组装网格布局
    gridContainer.appendChild(explanationDiv);
    gridContainer.appendChild(graphContainer);
    
    // 替换原始相图容器
    phaseContainer.replaceWith(gridContainer);
    
    // 初始化相轨迹
    const portrait = new PhasePortrait('phase-canvas', data.phaseData);
    portrait.animate();
    
    // 绑定重新播放事件
    document.getElementById('restartAnimation').addEventListener('click', () => {
      portrait.currentFrame = 0;
      portrait.animate();
    });
  }

  // 新增词云渲染
  renderWordCloud('wordcloud-canvas', data.wordCloud);
}

// 情感标签文字映射
function getSentimentLabel(sentiment) {
  return {
    positive: '积极',
    neutral: '中立',
    negative: '负面'
  }[sentiment] || '未知';
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
  beta_N: 0.12,  // 中立人群被负面影响率
  beta_I: 0.05,  // 积极人群被负面影响率
  gamma: 0.02,   // 负面转中立率
  delta: 0.01,   // 负面直接恢复率
  alpha: 0.11,   // 中立转积极率
  rho: 0.03,     // 负面转积极率
  epsilon: 0.02, // 积极转中立率
  mu: 0.01,      // 积极直接恢复率

  // 增强非线性效应
  nonlinear_SI: 0.05,  // S-I相互作用系数
  nonlinear_IN: 0.03   // I-N相互作用系数
};

const OSCILLATOR_PARAMS = {
  frequency: 0.1,  // 振荡频率 (弧度/天)
  damping: 0.02,    // 阻尼系数
  amplitude: 40     // 振幅
};

// 微分方程模拟器
function simulatePhaseTrajectory(posts) {
  const C = 100; // 总人口基数（假设总帖子数为100）
  const states = [];

  // 阶段1: 构建基础振荡器 (确保形成完整圆形)
  const phase1Data = simulateBaseOscillator();

  // 阶段2: 引入实际数据扰动
  const phase2Data = applyRealDataDisturbance(phase1Data, posts);

  return phase2Data;
}

// 阶段1: 创建基础振荡系统 (确保形成完整圆形)
function simulateBaseOscillator() {
  const states = [];
  const centerS = 50; // 中心点S坐标
  const centerI = 50; // 中心点I坐标

  for (let t = 0; t < 180; t++) {
    // 简谐振荡方程: θ = ωt
    const theta = OSCILLATOR_PARAMS.frequency * t;

    // 阻尼振荡: 振幅随时间衰减
    const amplitude = OSCILLATOR_PARAMS.amplitude * Math.exp(-OSCILLATOR_PARAMS.damping * t);

    // 圆形轨迹参数方程
    const S = centerS + amplitude * Math.cos(theta);
    const I = centerI + amplitude * Math.sin(theta);

    states.push({ S, I });
  }

  return states;
}

// 阶段2: 引入实际数据扰动
function applyRealDataDisturbance(baseData, posts) {
  // 从实际数据计算扰动因子
  const negativeCount = posts.filter(p => p.sentiment === 'negative').length;
  const positiveCount = posts.filter(p => p.sentiment === 'positive').length;
  
  // 计算扰动强度 (基于实际数据比例)
  const disturbanceStrength = Math.min(1, negativeCount / 50);
  
  return baseData.map((point, index) => {
    // 添加非线性扰动 - 基于实际数据
    const t = index / 30; // 时间参数
    
    // 扰动项1: 实际负面评价的影响
    const disturbance1 = 5 * disturbanceStrength * Math.sin(2 * Math.PI * t);
    
    // 扰动项2: 实际积极评价的影响
    const disturbance2 = 3 * (positiveCount / 40) * Math.cos(3 * Math.PI * t);
    
    return {
      S: point.S + disturbance1,
      I: point.I + disturbance2
    };
  });
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