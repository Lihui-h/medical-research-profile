// docs/js/login.js
document.addEventListener('DOMContentLoaded', function() {
  const loginForm = document.getElementById('loginForm');
  const errorBox = document.getElementById('loginError');

  // ==================== 工具函数 ====================
  const showError = (message) => {
    errorBox.textContent = message;
    errorBox.style.display = 'block';
    setTimeout(() => {
      errorBox.style.display = 'none';
    }, 5000);
  };

  // ==================== 核心登录逻辑 ====================
  loginForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // 清空旧状态
    errorBox.style.display = 'none';
    loginForm.querySelector('button[type="submit"]').disabled = true;

    // 获取输入值
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();

    // 输入验证
    if (!username || !password) {
      showError('请输入完整的机构代码和安全密钥');
      loginForm.querySelector('button[type="submit"]').disabled = false;
      return;
    }

    try {
      // 构建 API URL（注意新路径参数）
      const apiUrl = new URL('https://flask-api-git-main-lihui-hongs-projects.vercel.app/api/login');
      apiUrl.searchParams.append('path', 'api/login');
      apiUrl.searchParams.append('username', username);
      apiUrl.searchParams.append('password', password);

      // 发送请求
      const response = await fetch(apiUrl, {
        method: 'GET',
        mode: 'cors',
        cache: 'no-cache',
        headers: {
          'Accept': 'application/json'
        }
      });

      // 处理 HTTP 错误
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      // 解析 JSON
      const result = await response.json();

      // 处理业务逻辑错误
      if (!result.success) {
        throw new Error(result.error || '未知错误');
      }

      // 存储 token 并跳转
      localStorage.setItem('authToken', result.token);
      window.location.href = result.redirect;

    } catch (error) {
      console.error('登录失败:', error);
      showError(`登录失败: ${error.message.replace('HTTP 401: ', '')}`);

      // 特殊处理 Streamlit 认证拦截
      if (error.message.includes('Redirecting to /-/login')) {
        showError('系统检测到非常规访问，请直接访问数据驾驶舱完成首次认证');
        setTimeout(() => {
          window.location.href = 'https://medical-research-profile-ke2ztwqjq7z585fuompiq4.streamlit.app';
        }, 3000);
      }
    } finally {
      loginForm.querySelector('button[type="submit"]').disabled = false;
    }
  });

  // ==================== Token 自动续期 ====================
  const checkAuthStatus = () => {
    const authToken = localStorage.getItem('authToken');
    if (authToken) {
      fetch('https://medical-research-profile-ke2ztwqjq7z585fuompiq4.streamlit.app/?path=api/check_token', {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })
      .then(response => {
        if (!response.ok) localStorage.removeItem('authToken');
      })
      .catch(() => localStorage.removeItem('authToken'));
    }
  };

  // 每 5 分钟检查一次 token
  setInterval(checkAuthStatus, 300000);
  checkAuthStatus();
});