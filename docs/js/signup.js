// docs/js/signup.js
import { supabase } from './supabase.js'
document.addEventListener('DOMContentLoaded', () => {
  let lastSignupAttempt = 0;
  // 注册表单处理
  document.getElementById('signupForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    // 节流控制（10秒间隔）
    if (Date.now() - lastSignupAttempt < 10000) {
      alert('操作过于频繁，请稍后再试');
      return;
    }
    lastSignupAttempt = Date.now();
      
    const email = document.getElementById('signupEmail').value
    const password = document.getElementById('signupPassword').value
    const statusEl = document.getElementById('signupStatus')
  
    try {
      // 1. 用户注册
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            org_code: document.getElementById('orgCode').value
          }
        }
      })
  
      if (error) throw error
  
      // 2. 创建机构记录（需要RLS策略）
      const { error: dbError } = await supabase
        .from('organizations')
        .insert([{
          id: data.user.id,
          org_code: document.getElementById('orgCode').value,
          admin_email: email,
          access_level: 'basic'
        }])
  
      if (dbError) throw dbError
  
      statusEl.textContent = '✅ 注册成功！请检查邮箱验证'
      statusEl.style.color = 'green'
  
    } catch (error) {
      console.error('注册失败:', error)
      statusEl.textContent = `❌ 错误: ${error.message}`
      statusEl.style.color = 'red'
    }
  })
})