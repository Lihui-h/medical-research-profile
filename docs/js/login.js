// docs/js/login.js
document.addEventListener('DOMContentLoaded', function() {
  const loginForm = document.getElementById('loginForm');
  const errorBox = document.getElementById('loginError');

  function showError(message) {
    errorBox.textContent = message;
    errorBox.style.display = 'block';
    setTimeout(() => {
      errorBox.style.display = 'none';
    }, 5000);
  }

  loginForm.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();

    // 清空错误提示
    errorBox.textContent = '';
    errorBox.style.display = 'none';

    // 基本输入验证
    if (!username || !password) {
      showError('请输入完整的机构代码和安全密钥');
      return;
    }

    // 创建隐藏的 iframe 用于跨域通信
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    iframe.id = 'authFrame';
    
    // 构建 Streamlit API URL
    const streamlitAppUrl = 'https://medical-research-profile-ke2ztwqjq7z585fuompiq4.streamlit.app'; // 替换为你的实际地址
    const apiUrl = `${streamlitAppUrl}/?api=login&username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`;
    iframe.src = apiUrl;

    // 消息监听器
    function handleMessage(event) {
      // 验证消息来源
      if (event.origin !== streamlitAppUrl) return;

      try {
        const data = event.data;
        
        if (data.success) {
          // 存储 token 并跳转
          localStorage.setItem('authToken', data.token);
          window.location.href = data.redirect;
        } else {
          showError(data.error || '认证失败');
        }
      } catch (error) {
        showError('响应解析失败');
        console.error('Message handler error:', error);
      } finally {
        // 清理资源
        window.removeEventListener('message', handleMessage);
        document.body.removeChild(iframe);
      }
    }

    // 添加事件监听
    window.addEventListener('message', handleMessage);

    // 启动流程
    document.body.appendChild(iframe);

    // 超时处理
    const timeout = setTimeout(() => {
      showError('服务器响应超时，请稍后重试');
      window.removeEventListener('message', handleMessage);
      document.body.removeChild(iframe);
    }, 15000);

    // 清理超时计时器
    iframe.onload = function() {
      clearTimeout(timeout);
    };
  });
});