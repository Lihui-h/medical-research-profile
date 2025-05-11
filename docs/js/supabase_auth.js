import { supabase } from './supabase.js'

document.addEventListener('DOMContentLoaded', async () => {
    const { data: { session } } = await supabase.auth.getSession()
    
    if (session) {
    // 隐藏主页内容
    document.querySelector('.overbg').style.display = 'none'
    // 显示仪表盘容器
    document.getElementById('dashboard').style.display = 'block'
    // 初始化仪表盘
    initDashboard(session)
    }
})

async function initDashboard(session) {
    // 动态创建仪表盘结构
    const dashboardEl = document.getElementById('dashboard')
    dashboardEl.innerHTML = `
    <div class="dashboard-header">
        <h2>${session.user.email}的数据舱</h2>
        <button onclick="handleLogout()">退出</button>
    </div>
    <div id="dashboard-content"></div>
    `

    // 加载数据模块
    loadDataMetrics(session.user.id)
}