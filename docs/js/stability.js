// docs/js/stability.js
class StabilityAnalyzer {
    constructor() {
      this.params = {
        α: 0.3,  // 中立转积极率
        β_N: 0.2, // 中立被负面影响率
        β_I: 0.1, // 积极被负面影响率
        γ: 0.15,  // 负面转中立率
        δ: 0.05,  // 负面转恢复率
        ρ: 0.25,  // 负面转积极率
        ε: 0.1,   // 积极转中立率
        μ: 0.08,  // 积极转恢复率
        ζ: 0.03   // 恢复转中立率
      };
    }
  
    // 欧拉法数值求解
    simulate(sentimentScores) {
      const dt = 1; // 时间步长（按天）
      const states = [];
      
      // 初始状态（假设初始人群分布）
      let S = sentimentScores.filter(s => s <= -3).length;
      let I = sentimentScores.filter(s => s >= 3).length;
      let N = sentimentScores.filter(s => s > -3 && s < 3).length;
      let R = 0;
  
      for (const score of sentimentScores) {
        // 微分方程组计算
        const dS = (this.params.β_N * N) + (this.params.β_I * I) 
                 - (this.params.γ + this.params.δ) * S;
        
        const dI = (this.params.α * N) + (this.params.ρ * S) 
                 - (this.params.ε + this.params.μ) * I;
        
        const dN = (this.params.γ * S) + (this.params.ε * I) + (this.params.ζ * R) 
                 - (this.params.α + this.params.β_N + this.params.β_I) * N;
        
        const dR = (this.params.δ * S) + (this.params.μ * I) 
                 - (this.params.ζ * R);
  
        // 更新状态
        S += dS * dt;
        I += dI * dt;
        N += dN * dt;
        R += dR * dt;
  
        // 记录稳定性指数（积极人群占比变化率）
        states.push({
          date: new Date().toISOString(), // 需替换为实际日期
          stability: dI/I * 100 || 0 // 积极人群变化率百分比
        });
      }
  
      return states;
    }
  }