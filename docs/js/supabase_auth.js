// docs/js/supabase_auth.js
import { supabase } from './supabase.js'

// 全局错误处理器
window.handleDashboardError = (error) => {
  console.error('仪表盘错误:', error)
  const container = document.getElementById('dashboard-content')
  if (container) {
    container.innerHTML = `
      <div class="error-state">
        <h3>⚠️ 数据加载失败</h3>
        <p>${error.message}</p>
        <button onclick="location.reload()">重试</button>
      </div>
    `
  }
}

// 主认证逻辑
window.initAuth = async () => {
  try {
    const { data: { session } } = await supabase.auth.getSession()
    
    if (session) {
      // 隐藏登录界面
      document.querySelector('.overbg').style.display = 'none'
      const dashboardContainer = document.getElementById('dashboard')
      dashboardContainer.style.display = 'block'

      // 动态加载仪表盘模块
      const { loadDataMetrics, renderDashboard } = await import('./dashboard.js')
      
      // 加载数据（带错误捕获）
      const data = await loadDataMetrics(session.user.id)
        .catch(handleDashboardError)

      // 渲染界面（仅在数据有效时）
      if (data) {
        renderDashboard('dashboard-content', data)
        initLogoutButton() // 初始化退出按钮
      }
    }
  } catch (error) {
    handleDashboardError(error)
  }
}

// 退出功能初始化
function initLogoutButton() {
  const logoutBtn = document.getElementById('logoutBtn')
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async () => {
      await supabase.auth.signOut()
      window.location.reload()
    })
  }
}

// 初始化认证状态监听
document.addEventListener('DOMContentLoaded', () => {
  initAuth()
  supabase.auth.onAuthStateChange((_event, session) => {
    if (session) initAuth() // 自动刷新数据状态
  })
})