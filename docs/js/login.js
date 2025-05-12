// login.js 完整实现
import { supabase } from './supabase.js'
document.addEventListener('DOMContentLoaded', () => {
  // 登录表单处理
  document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault()
    
    const email = document.getElementById('email').value
    const password = document.getElementById('password').value
    const statusEl = document.getElementById('loginStatus')

    try {
      // 1. 密码登录
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password
      })

      if (error) throw error

      // 2. 触发动态渲染（不再跳转）
      window.dispatchEvent(new CustomEvent('login-success', {
        detail: { session: data.session }
      }))

    } catch (error) {
      console.error('登录失败:', error)
      statusEl.textContent = `❌ 错误: ${error.message}`
      statusEl.style.color = 'red'
    }
  })
})