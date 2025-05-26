// docs/js/phase-portrait.js
export class PhasePortrait {
    constructor(canvasId, data) {
      this.canvas = document.getElementById(canvasId);
      this.ctx = this.canvas.getContext('2d');
      this.data = data; // 格式：[{ S: 6, I: 4 }, { S: 5, I: 3 }, ...]
      this.animationId = null;
      this.currentFrame = 0;
      this.timeScale = 1;
  
      // 初始化画布
      this.canvas.width = 600;
      this.canvas.height = 400;
      this.setupEventListeners();
  
      // 动态计算坐标范围（基于数据极值）
      this.xMin = Math.min(...this.data.map(d => d.S)) * 0.9;
      this.xMax = Math.max(...this.data.map(d => d.S)) * 1.1;
      this.yMin = Math.min(...this.data.map(d => d.I)) * 0.9;
      this.yMax = Math.max(...this.data.map(d => d.I)) * 1.1;
    }
  
    // 坐标映射（动态范围）
    mapToCanvas(x, y) {
      return {
        x: (x - this.xMin) * (this.canvas.width / (this.xMax - this.xMin)),
        y: this.canvas.height - (y - this.yMin) * (this.canvas.height / (this.yMax - this.yMin))
      };
    }
  
    // 轨迹颜色渐变（时间维度）
    getTrajectoryColor(frameIndex) {
      const hue = (frameIndex / this.data.length) * 240; // 蓝 → 红
      return `hsl(${hue}, 100%, 50%)`;
    }
  
    // 绘制单帧
    drawFrame() {
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  
      // 绘制历史轨迹
      for (let i = 1; i <= this.currentFrame; i++) {
        const prev = this.data[i - 1];
        const curr = this.data[i];
        const prevPos = this.mapToCanvas(prev.S, prev.I);
        const currPos = this.mapToCanvas(curr.S, curr.I);
  
        this.ctx.beginPath();
        this.ctx.moveTo(prevPos.x, prevPos.y);
        this.ctx.lineTo(currPos.x, currPos.y);
        this.ctx.strokeStyle = this.getTrajectoryColor(i);
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
      }
  
      // 绘制当前点
      const current = this.data[this.currentFrame];
      const pos = this.mapToCanvas(current.S, current.I);
      this.ctx.fillStyle = '#2196F3';
      this.ctx.beginPath();
      this.ctx.arc(pos.x, pos.y, 4, 0, Math.PI * 2);
      this.ctx.fill();
  
      // 绘制平衡点（示例值，需根据实际计算）
      const equilibriumPos = this.mapToCanvas(5, 3);
      this.ctx.fillStyle = 'rgba(255, 0, 0, 0.3)';
      this.ctx.beginPath();
      this.ctx.arc(equilibriumPos.x, equilibriumPos.y, 12, 0, Math.PI * 2);
      this.ctx.fill();
    }
  
    // 动画循环
    animate() {
      if (this.currentFrame >= this.data.length - 1) {
        cancelAnimationFrame(this.animationId);
        return;
      }
  
      this.drawFrame();
      this.currentFrame++;
  
      this.animationId = requestAnimationFrame(() => 
        setTimeout(() => this.animate(), 100 / this.timeScale)
      );
    }
  
    // 事件监听
    setupEventListeners() {
      document.getElementById('restartAnimation').addEventListener('click', () => {
        this.currentFrame = 0;
        this.animate();
      });
  
      document.getElementById('timeScale').addEventListener('input', (e) => {
        this.timeScale = parseFloat(e.target.value);
      });
    }
  }