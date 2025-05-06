//docs/js/loaded.js
// 在DOMContentLoaded事件内初始化
document.addEventListener('DOMContentLoaded', function() {
  // ==================== 平滑滚动处理 ====================
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    // 新增：跳过有 data-target 属性的元素
    if (anchor.hasAttribute('data-target')) return;
    
    anchor.addEventListener('click', function(e) {
      e.preventDefault();
      const targetId = this.getAttribute('href');

      // 新增校验：排除无效锚点
      if (!targetId || targetId === '#') {
        console.warn('检测到无效锚点:', this);
        return;
      }

      const target = document.querySelector(targetId);
      if (target) {
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
        history.pushState(null, null, targetId);
      } else {
        console.error(`锚点目标不存在: ${targetId}`);
      }
    });
  });

  // ==================== 滚动动画检测 ====================
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      const element = entry.target;
      if (entry.isIntersecting) {
        element.classList.add('animate');
        observer.unobserve(element);
      }
    });
  }, {
    threshold: 0.15,
    rootMargin: '0px 0px -50px 0px'
  });

  document.querySelectorAll('.imgcircle').forEach(el => {
    observer.observe(el);
  });

  // ==================== 滚动节流优化 ====================
  let lastScroll = 0;
  const scrollHandler = () => {
    const now = Date.now();
    if (now - lastScroll > 100) {
      lastScroll = now;
    }
  };
  
  window.addEventListener('scroll', scrollHandler);
});
