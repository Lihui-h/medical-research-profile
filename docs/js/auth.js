// docs/js/auth.js
// 在DOM加载完成后添加以下代码
document.addEventListener('DOMContentLoaded', () => {
    // 获取模态框元素
    const authModal = document.getElementById('authModal')
    const closeBtn = authModal.querySelector('.close')
    
    // 绑定组织/公司按钮点击事件
    document.querySelector('[data-target="#authModal"]').addEventListener('click', function(e) {
        e.preventDefault() // 阻止默认跳转行为
        authModal.style.display = 'block' // 显示模态框
    })

    // 绑定关闭按钮事件
    closeBtn.addEventListener('click', () => {
        authModal.style.display = 'none'
    })

    // 点击模态框外部关闭
    window.addEventListener('click', (e) => {
        if (e.target === authModal) {
        authModal.style.display = 'none'
        }
    })

    // 标签切换逻辑（保持原有代码）
    const tabs = document.querySelectorAll('.tab')
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
        const tabName = tab.dataset.tab
        tabs.forEach(t => t.classList.remove('active'))
        tab.classList.add('active')
        document.querySelectorAll('.auth-form').forEach(form => {
            form.classList.toggle('active', form.id === `${tabName}Form`)
        })
        })
    })
    })