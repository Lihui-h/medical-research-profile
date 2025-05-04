// docs/js/login.js
document.addEventListener('DOMContentLoaded', function() {
  const loginForm = document.getElementById('loginForm');
  const errorBox = document.getElementById('loginError');

  // 阻止表单默认提交
  loginForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();

    // 清空错误提示
    errorBox.textContent = '';
    errorBox.style.display = 'none';

    try {
      // 发送登录请求
      const response = await fetch('https://medical-research-profile-ybuh3unpzstrb9hp9lrk6s.streamlit.app/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      const result = await response.json();

      if (result.success) {
        // 存储认证状态（示例使用 sessionStorage）
        sessionStorage.setItem('authToken', 'valid');
        // 跳转到仪表盘
        window.location.href = result.redirect;
      } else {
        showError(result.error || '登录失败');
      }
    } catch (error) {
      showError('网络错误，请检查连接');
      console.error('API请求失败:', error);
    }
  });

  function showError(message) {
    errorBox.textContent = message;
    errorBox.style.display = 'block';
    setTimeout(() => {
      errorBox.style.display = 'none';
    }, 3000);
  }
});