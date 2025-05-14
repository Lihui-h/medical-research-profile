// supabase_auth.js
import { supabase } from './supabase.js'

// 全局状态标识
let authInitialized = false
let authStateListenerAttached = false

// 错误处理函数
window.handleDashboardError = (error) => {
  console.error('仪表盘错误:', error)
  const container = document.getElementById('dashboard-content')
  
  // 显示错误信息
  if (container) {
    container.innerHTML = `
      <div class="error-state">
        <h3>⚠️ 系统暂时不可用</h3>
        <p>${error.message || '未知错误'}</p>
        <button onclick="window.location.reload()">刷新重试</button>
      </div>
    `
  }
  
  // 恢复界面状态
  document.body.classList.remove('dashboard-active')
  document.querySelector('.overbg').style.display = 'block'
}

// 主初始化函数
window.initAuth = async () => {
  try {
    // 幂等性检查
    if (authInitialized) {
      console.log('认证系统已初始化，跳过重复操作')
      return
    }
    authInitialized = true

    // 获取当前会话
    const { data: { session }, error } = await supabase.auth.getSession()
    if (error) throw error

    console.log('初始会话状态:', session ? '已登录' : '未登录')

    // 处理登录状态
    if (session) {
      await handleAuthenticatedState(session)
    }
  } catch (error) {
    handleDashboardError(error)
    authInitialized = false // 允许重试
  }
}

// 认证成功处理
async function handleAuthenticatedState(session) {
  // 界面状态切换
  document.body.classList.add('dashboard-active')
  const dashboard = document.getElementById('dashboard')
  dashboard.style.display = 'block'

  // 关闭模态框
  const authModal = document.getElementById('authModal')
  if (authModal) authModal.style.display = 'none'

  // 动态加载仪表盘模块
  try {
    const { loadDataMetrics, renderDashboard } = await import('./dashboard.js')
    const data = await loadDataMetrics(session.user.id)
    renderDashboard('dashboard-content', data)
    initLogoutButton()
  } catch (error) {
    handleDashboardError(error)
  }
}

// 退出功能
function initLogoutButton() {
  const logoutBtn = document.getElementById('logoutBtn')
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async () => {
      await supabase.auth.signOut()
      document.body.classList.remove('dashboard-active')
      window.location.reload()
    })
  }
}

// 认证状态监听器（单例模式）
function setupAuthStateListener() {
  if (authStateListenerAttached) return
  authStateListenerAttached = true

  supabase.auth.onAuthStateChange((event, session) => {
    console.log('认证状态变更事件:', event)
    
    switch(event) {
      case 'INITIAL_SESSION':
        // 不处理初始状态
        break
      case 'SIGNED_IN':
        handleAuthenticatedState(session)
        break
      case 'SIGNED_OUT':
        document.body.classList.remove('dashboard-active')
        break
      default:
        console.log('未处理的状态变更:', event)
    }
  })
}

// DOM就绪后初始化
document.addEventListener('DOMContentLoaded', () => {
  if (!authInitialized) {
    initAuth()
    setupAuthStateListener()
  }
})