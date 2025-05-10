// login.js 完整实现
document.addEventListener('DOMContentLoaded', () => {
  // 登录表单处理
  document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault()
    
    const email = document.getElementById('email').value
    const password = document.getElementById('password').value
    const statusEl = document.getElementById('loginStatus')

    try {
      // 1. 密码登录
      const { data, error } = await window.supabase.auth.signInWithPassword({
        email,
        password
      })

      if (error) throw error

      // 2. 获取机构信息
      const { data: orgData, error: orgError } = await window.supabase
        .from('organizations')
        .select('org_code, access_level')
        .eq('admin_email', email)
        .single()

      if (orgError) throw orgError

      // 3. 存储会话
      localStorage.setItem('supabase_session', JSON.stringify(data.session))
      window.location.href = 'dashboard.html'

    } catch (error) {
      console.error('登录失败:', error)
      statusEl.textContent = `❌ 错误: ${error.message}`
      statusEl.style.color = 'red'
    }
  })
})