// docs/js/supabase_auth.js
import { supabase } from './supabase.js'

window.initAuth = async () => {
  const { data: { session } } = await supabase.auth.getSession()
  
  if (session) {
    // 动态加载dashboard模块
    const { loadDataMetrics, renderDashboard } = await import('./dashboard.js')
    
    // 隐藏登录界面
    document.querySelector('.overbg').style.display = 'none'
    const dashboardContainer = document.getElementById('dashboard')
    dashboardContainer.style.display = 'block'

    // 加载并渲染数据
    const data = await loadDataMetrics(session.user.id)
    renderDashboard('dashboard-content', data)
  }
}