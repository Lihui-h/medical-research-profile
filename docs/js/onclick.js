// onclick.js 修改后代码
document.addEventListener("DOMContentLoaded", function () {
	// 1. 菜单切换功能（对应导航栏的展开/收起）
	const menuToggle = document.querySelector(".menuToggle");
	const navbarNav = document.querySelector(".nav.navbar-nav.menu"); // 对应你的导航菜单
	
	if (menuToggle && navbarNav) {
	  menuToggle.addEventListener("click", function() {
		console.log("导航菜单切换");
		navbarNav.classList.toggle("active");
		// 添加动画效果
		navbarNav.style.transition = "all 0.3s ease";
	  });
	}
  
	// 2. 登录模态框控制（Bootstrap原生功能保留）
	// 不需要额外JS，保留data-toggle特性即可
  });