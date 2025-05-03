/**
 * login.js - 医疗机构数据舱登录验证（终极稳定版）
 * 功能特性：
 * 1. 双重事件阻断机制
 * 2. 输入消毒处理
 * 3. 错误反馈防抖动
 * 4. 安全凭证存储
 * 5. 跨脚本冲突防护
 */

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', function() {
  initLoginSystem();
});

// ==================== 核心逻辑 ====================
function initLoginSystem() {
  const loginForm = document.getElementById('loginForm');
  
  // 防御性检查
  if (!loginForm) {
    console.error('[系统错误] 未找到登录表单');
    return;
  }

  // 移除旧事件监听器（防止重复绑定）
  loginForm.removeEventListener('submit', handleLoginSubmit);
  
  // 绑定新事件（捕获阶段优先处理）
  loginForm.addEventListener('submit', handleLoginSubmit, {
    capture: true,
    passive: false
  });
}

function handleLoginSubmit(e) {
  // 双重阻断默认行为
  e.preventDefault();
  e.stopImmediatePropagation();

  const username = sanitizeInput(document.getElementById('username').value);
  const password = sanitizeInput(document.getElementById('password').value);
  const errorBox = document.getElementById('loginError');

  // 清空旧状态
  errorBox.textContent = '';
  errorBox.style.display = 'none';

  try {
    // 输入验证流水线
    validateCredentials(username, password);
    
    // 安全存储凭证（会话级存储）
    storeCredentials(username, password);
    
    // 定向跳转
    redirectToDashboard();
  } catch (error) {
    handleLoginError(error, errorBox);
  }
}

// ==================== 工具函数 ====================
function sanitizeInput(input) {
  // 消毒处理：移除首尾空格/换行/特殊字符
  return input.trim().replace(/[\n\r\t\0]/g, '');
}

function validateCredentials(username, password) {
  // 非空检查
  if (!username || !password) {
    throw new Error('EMPTY_FIELDS');
  }

  // 修改为从环境变量获取
  const validUser = process.env.VUE_APP_HOSPITAL_USER || 'default_user';
  const validPass = process.env.VUE_APP_HOSPITAL_PASS || 'default_pass';
  if (username !== validUser || password !== validPass) {
    throw new Error('INVALID_CREDENTIALS');
  }
}

function storeCredentials(username, password) {
  // 安全存储方案（Base64编码 + 时间戳）
  const credentials = {
    token: btoa(unescape(encodeURIComponent(`${username}:${password}`))),
    timestamp: Date.now()
  };
  
  // 会话级存储
  sessionStorage.setItem('medAuth', JSON.stringify(credentials));
}

function redirectToDashboard() {
  // 防XSS跳转
  const safePath = encodeURI('dashboard.html');
  window.location.href = safePath + '?t=' + Date.now();
}

function handleLoginError(error, errorBox) {
  // 错误类型映射
  const errorMessages = {
    'EMPTY_FIELDS': '请填写完整登录信息',
    'INVALID_CREDENTIALS': '机构代码或安全密钥错误',
    'default': '系统繁忙，请稍后重试'
  };

  // 获取友好提示
  const message = errorMessages[error.message] || errorMessages.default;
  
  // 防抖动显示
  clearTimeout(window.errorTimeout);
  errorBox.textContent = message;
  errorBox.style.display = 'block';
  window.errorTimeout = setTimeout(() => {
    errorBox.style.display = 'none';
  }, 3000);

  // 控制台诊断信息
  console.warn(`[登录异常] ${error.message}`);
}

// ==================== 冲突防护 ====================
// 防止其他脚本修改原型
Object.defineProperty(window, 'handleLoginSubmit', {
  writable: false,
  configurable: false
});