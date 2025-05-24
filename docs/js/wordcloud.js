// docs/js/wordcloud.js
export function renderWordCloud(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) {
      console.error('词云容器不存在');
      return;
    }
  
    // 清空旧内容
    container.innerHTML = '';
  
    // 数据格式转换
    const wordList = data.map(item => [item.word, item.count]);
  
    // 容错处理
    if (wordList.length === 0) {
      container.innerHTML = '<div class="empty-tip">暂无词云数据</div>';
      return;
    }
  
    // 生成词云
    try {
      WordCloud(container, {
        list: wordList,
        gridSize: 12,
        weightFactor: 8,
        fontFamily: 'Microsoft Yahei, sans-serif',
        color: (word, weight) => {
          // 根据情感值返回颜色
          const sentiment = data.find(d => d.word === word)?.sentiment || 0;
          return sentiment > 0 ? '#4CAF50' : sentiment < 0 ? '#F44336' : '#9E9E9E';
        },
        rotateRatio: 0.3,
        shape: 'circle', // 可选：cardioid/diamond/triangle...
        backgroundColor: '#f8f9fa'
      });
    } catch (e) {
      console.error('词云生成失败:', e);
      container.innerHTML = '<div class="error-tip">词云渲染异常</div>';
    }
  }