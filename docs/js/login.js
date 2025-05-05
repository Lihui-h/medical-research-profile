// docs/js/login.js
document.addEventListener('DOMContentLoaded', function() {
  const loginForm = document.getElementById('loginForm');
  const errorBox = document.getElementById('loginError');

  loginForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();

    // 清空错误提示
    errorBox.textContent = '';
    errorBox.style.display = 'none';

    try {
      // 调用 Streamlit 后端 API
      const apiUrl = `https://medical-research-profile-ybuh3unpzstrb9hp9lrk6s.streamlit.app/?api=login&username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`;
      const response = await fetch(apiUrl
        , {
          mode: 'cors', // 允许跨域请求
          credentials: 'include', // 允许携带 cookie 
        }
      );
      
      if (!response.ok) {
        throw new Error(`HTTP 错误 ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        // 存储 Token 到 localStorage
        localStorage.setItem('authToken', result.token);
        // 跳转到数据看板
        window.location.href = result.redirect;
      } else {
        showError(result.error || '未知错误');
      }
    } catch (error) {
      showError(`请求失败: ${error.message}`);
      console.error('API 错误:', error);
    }
  });

  function showError(message) {
    errorBox.textContent = message;
    errorBox.style.display = 'block';
    setTimeout(() => {
      errorBox.style.display = 'none';
    }, 5000);
  }
});