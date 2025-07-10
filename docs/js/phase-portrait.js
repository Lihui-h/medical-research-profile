// docs/js/phase-portrait.js
export class PhasePortrait {
    constructor(canvasId, data) {
      this.canvas = document.getElementById(canvasId);
      if (!this.canvas) {
        console.error(`Canvas element with ID '${canvasId}' not found`);
        return;
      }
      this.ctx = this.canvas.getContext('2d');
      this.data = data; // 格式：[{ S: 6, I: 4 }, { S: 5, I: 3 }, ...]
      this.animationId = null;
      this.currentFrame = 0;
      this.timeScale = 1;
  
      // 初始化画布
      this.canvas.width = 600;
      this.canvas.height = 400;
  
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

    drawGrid() {
        // 动态网格绘制
        this.ctx.strokeStyle = '#eee';
        this.ctx.setLineDash([2, 3]);
    
        // X轴网格
        for (let x = 0; x <= this.canvas.width; x += this.canvas.width / 10) {
          this.ctx.beginPath();
          this.ctx.moveTo(x, 0);
          this.ctx.lineTo(x, this.canvas.height);
          this.ctx.stroke();
        }
    
        // Y轴网格
        for (let y = 0; y <= this.canvas.height; y += this.canvas.height / 10) {
          this.ctx.beginPath();
          this.ctx.moveTo(0, y);
          this.ctx.lineTo(this.canvas.width, y);
          this.ctx.stroke();
        }
        this.ctx.setLineDash([]);
    }

    drawAxes() {
        // 坐标轴样式
        this.ctx.strokeStyle = '#666';
        this.ctx.lineWidth = 1;
        this.ctx.font = '12px Arial';
        this.ctx.fillStyle = '#333';

        // X轴
        this.ctx.beginPath();
        this.ctx.moveTo(0, this.canvas.height);
        this.ctx.lineTo(this.canvas.width, this.canvas.height);
        this.ctx.stroke();

        // Y轴
        this.ctx.beginPath();
        this.ctx.moveTo(0, 0);
        this.ctx.lineTo(0, this.canvas.height);
        this.ctx.stroke();

        // 刻度标签（X轴）
        const xTicks = 5;
        for (let i = 0; i <= xTicks; i++) {
            const xVal = this.xMin + (i / xTicks) * (this.xMax - this.xMin);
            const xPos = i * (this.canvas.width / xTicks);
            this.ctx.fillText(xVal.toFixed(1), xPos - 10, this.canvas.height - 5);
        }

        // 刻度标签（Y轴）
        const yTicks = 5;
        for (let i = 0; i <= yTicks; i++) {
            const yVal = this.yMin + (i / yTicks) * (this.yMax - this.yMin);
            const yPos = this.canvas.height - i * (this.canvas.height / yTicks);
            this.ctx.fillText(yVal.toFixed(1), 5, yPos + 5); 
        }
    }
  
    // 轨迹颜色渐变（时间维度）
    getTrajectoryColor(frameIndex) {
      const hue = (frameIndex / this.data.length) * 240; // 蓝 → 红
      return `hsl(${hue}, 100%, 50%)`;
    }
  
    // 绘制单帧
    drawFrame() {
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      this.drawGrid();
      this.drawAxes();
  
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
  
  // 添加新方法用于绑定重启按钮
  bindRestartButton(buttonElement) {
    if (!buttonElement) {
      console.warn("无效的重启按钮元素");
      return;
    }
    
    this.restartButton = buttonElement;
    this.restartButton.addEventListener('click', () => {
      this.currentFrame = 0;
      this.animate();
    });
  }

  restartAnimation() {
    // 停止当前动画
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
    
    // 重置到第一帧
    this.currentFrame = 0;
    
    // 重新开始动画
    this.animate();
  }
  
  animate() {
    if (this.currentFrame >= this.data.length - 1) {
      cancelAnimationFrame(this.animationId);
      return;
    }
    
    this.drawFrame();
    this.currentFrame++;
    
    this.animationId = requestAnimationFrame(() => {
      setTimeout(() => this.animate(), 100 / this.timeScale);
    });
  }
}