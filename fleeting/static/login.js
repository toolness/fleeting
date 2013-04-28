$(window).ready(function() {
  var csrfToken = $('meta[name="csrf"]').attr('content');

  $(".js-logout").click(function() {
    jQuery.post("/logout", {
      _csrf_token: csrfToken
    }, function(text) {
      window.location.reload();
    });
  });
  $(".js-login").click(function() {
    navigator.id.get(function(assertion) {
      if (!assertion) return;

      jQuery.post("/login", {
        assertion: assertion,
        _csrf_token: csrfToken
      }, function(text) {
        window.location.reload();
      });
    });
  });
});
