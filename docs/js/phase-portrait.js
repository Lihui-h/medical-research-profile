// docs/js/phase-portrait.js
export class PhasePortrait {
    constructor(canvasId, data) {
      this.canvas = document.getElementById(canvasId);
      this.ctx = this.canvas.getContext('2d');
      this.data = data; // 包含时间序列的模型状态数据
      this.animationId = null;
      this.currentFrame = 0;
      this.timeScale = 1;
  
      // 初始化画布
      this.canvas.width = 600;
      this.canvas.height = 400;
      this.setupEventListeners();
    }
  
    // 坐标映射（模型状态 → 画布坐标）
    mapToCanvas(x, y) {
        // 动态计算范围（基于实际数据极值）
        const xMin = Math.min(...this.data.map(d => d.S));
        const xMax = Math.max(...this.data.map(d => d.S));
        const yMin = Math.min(...this.data.map(d => d.I));
        const yMax = Math.max(...this.data.map(d => d.I));
      
        return {
            x: (x - xMin) * (this.canvas.width / (xMax - xMin + 1)),
            y: this.canvas.height - (y - yMin) * (this.canvas.height / (yMax - yMin + 1)) 
        };
    }
  
    // 绘制单个帧
    drawFrame() {
        // 添加数据校验
        if (!this.data[this.currentFrame]) {
            console.error('无效的数据帧:', this.currentFrame);
            return;
        }
        const currentState = this.data[this.currentFrame];
        const { x, y } = this.mapToCanvas(currentState.S, currentState.I); // S: 负面人群, I: 积极人群
  
        // 绘制轨迹线
        if (this.currentFrame > 0) {
            const prevState = this.data[this.currentFrame - 1];
            const prevPos = this.mapToCanvas(prevState.S, prevState.I);
            this.ctx.beginPath();
            this.ctx.moveTo(prevPos.x, prevPos.y);
            this.ctx.lineTo(x, y);
            this.ctx.strokeStyle = this.getColorByStability(currentState);
            this.ctx.lineWidth = 2;
            this.ctx.stroke();
        }
  
        // 绘制当前点
        this.ctx.fillStyle = '#2196F3';
        this.ctx.beginPath();
        this.ctx.arc(x, y, 3, 0, Math.PI * 2);
        this.ctx.fill();
  
        // 更新帧
        this.currentFrame = (this.currentFrame + 1) % this.data.length;
    }
  
    // 根据稳定性指数生成颜色
    getColorByStability(state) {
      const stability = state.dI / state.I; // 积极人群变化率
      return stability > 0 ? '#4CAF50' : '#F44336'; // 绿色: 稳定增长, 红色: 不稳定衰减
    }
  
    // 动画循环
    animate() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.drawFrame();
        this.currentFrame++;
        // 修改动画循环逻辑（完整播放后暂停）
        if (this.currentFrame >= this.data.length - 1) {
            cancelAnimationFrame(this.animationId); // 停止动画
            this.currentFrame = 0; // 重置为初始状态
            return; // 避免重复调用
        }
        this.animationId = requestAnimationFrame(() => 
            setTimeout(() => this.animate(), 100 / this.timeScale)
        );
    }
  
    // 事件监听
    setupEventListeners() {
      document.getElementById('restartAnimation').addEventListener('click', () => {
        this.currentFrame = 0;
      });
  
      document.getElementById('timeScale').addEventListener('input', (e) => {
        this.timeScale = parseFloat(e.target.value);
      });
    }
  }