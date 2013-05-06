"use strict";

$(window).on('load', function() {
  $('[data-refresh-url]').each(function() {
    var $this = $(this);
    var url = $this.attr('data-refresh-url');
    var interval = parseInt($this.attr('data-refresh-seconds')) * 1000;

    setInterval(function() { $this.load(url); }, interval);
  });
});
