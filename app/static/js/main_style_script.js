/**
 * Elektron - An Admin Toolkit
 * @version 0.3.1
 * @license MIT
 * @link https://github.com/onokumus/elektron#readme
 */
'use strict';

/* eslint-disable no-undef */
$(function () {
	if ($(window).width() < 992) {
		$('#app-side').onoffcanvas('hide');
	} else {
		$('#app-side').onoffcanvas('show');
	}

	$('.side-nav .unifyMenu').unifyMenu({ toggle: true });

	$('#app-side-hoverable-toggler').on('click', function () {
		$('.app-side').toggleClass('is-hoverable');
		$(undefined).children('i.fa').toggleClass('fa-angle-right fa-angle-left');
	});

	$('#app-side-mini-toggler').on('click', function () {
		$('.app-side').toggleClass('is-mini');
		$("#app-side-mini-toggler i").toggleClass('fa-chart-bar fa-bars');
	});

	$('#onoffcanvas-nav').on('click', function () {
		$('.app-side').toggleClass('left-toggle');
		$('.app-main').toggleClass('left-toggle');
		$("#onoffcanvas-nav i").toggleClass('fa-chart-bar fa-bars');
	});

	$('.onoffcanvas-toggler').on('click', function () {
		$(".onoffcanvas-toggler i").toggleClass('fa-solid fa-circle-chevron-right fa-solid fa-circle-chevron-left');
	});
});


$(function() {
	$('#unifyMenu')
	.unifyMenu();
});


// Bootstrap Tooltip
$(function () {
	$('[data-toggle="tooltip"]').tooltip()
})

// Task list
$('.task-list').on('click', 'li.list', function() {
	$(this).toggleClass('completed');
});


// Loading
$(function() {
	$(".loading-wrapper").fadeOut(500);
});
