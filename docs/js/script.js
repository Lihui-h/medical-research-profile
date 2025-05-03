/*
Theme: Flatfy Theme
Author: Andrea Galanti
Bootstrap Version 
Build: 1.0

*/

$(window).load(function() { 
	//Preloader 
	$('#status').delay(300).fadeOut(); 
	$('#preloader').delay(300).fadeOut('slow');
	$('body').delay(550).css({'overflow':'visible'});
})

$(document).ready(function() {
		//animated logo
		$(".navbar-brand").hover(function () {
			$(this).toggleClass("animated shake");
		});
		
		//animated scroll_arrow
		$(".img_scroll").hover(function () {
			$(this).toggleClass("animated infinite bounce");
		});
		
		
		//MagnificPopup
		$('.image-link').magnificPopup({type:'image'});


		// OwlCarousel N1
		$("#owl-demo").owlCarousel({
			autoPlay: 3000,
			items : 3,
			itemsDesktop : [1199,3],
			itemsDesktopSmall : [979,3]
		});

		// OwlCarousel N2
		$("#owl-demo-1").owlCarousel({
			  //navigation : false, // Show next and prev buttons
			  autoPlay: 3000,
			  slideSpeed : 300,
			  paginationSpeed : 400,
			  singleItem:true
		});
		
		// OwlCarousel N3
		$("#owl-demo-2").owlCarousel({
			  //navigation : false, // Show next and prev buttons
			  autoPlay: 3000,
			  slideSpeed : 300,
			  paginationSpeed : 400,
			  singleItem:true
		});
		
		// OwlCarousel N4
		$("#owl-demo-3").owlCarousel({
			  //navigation : false, // Show next and prev buttons
			  autoPlay: 3000,
			  slideSpeed : 300,
			  paginationSpeed : 400,
			  singleItem:true
		});
		
		// OwlCarousel N5
		$("#owl-demo-4").owlCarousel({
			  //navigation : false, // Show next and prev buttons
			  autoPlay: 3000,
			  slideSpeed : 300,
			  paginationSpeed : 400,
			  singleItem:true
		});

		//SmothScroll
		$('a[href*=#]').click(function() {
			if (location.pathname.replace(/^\//,'') == this.pathname.replace(/^\//,'')
			&& location.hostname == this.hostname) {
					var $target = $(this.hash);
					$target = $target.length && $target || $('[name=' + this.hash.slice(1) +']');
					if ($target.length) {
							var targetOffset = $target.offset().top;
							$('html,body').animate({scrollTop: targetOffset}, 600);
							return false;
					}
			}
		});
		
		//Subscribe
		//new UIMorphingButton( document.querySelector( '.morph-button' ) );
		//uiMorphingButton_inflow.js里51行去掉this后，上面这行无效化
		// for demo purposes only
		/*这一段该死的劫持了login.js，犯人去死[].slice.call( document.querySelectorAll( 'form button' ) ).forEach( function( bttn ) { 
			bttn.addEventListener( 'click', function( ev ) { ev.preventDefault(); } );
		} );
		*/

});

