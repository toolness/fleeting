window.reloadPage = function() {
  // We bind this to a global so we can stub it out in test suites, as
  // location.reload can't be stubbed.
  location.reload();
};

(function() {
  var csrfToken = $('meta[name="csrf"]').attr('content');
  var email = $('meta[name="email"]').attr('content') || null;

  navigator.id.watch({
    loggedInUser: email,
    onlogin: function(assertion) {
      $.post("/login", {
        assertion: assertion,
        _csrf_token: csrfToken
      }, reloadPage);
    },
    onlogout: function() {
      $.post("/logout", {
        _csrf_token: csrfToken
      }, reloadPage);      
    }
  });

  $("body").on("click", ".js-login", function() { navigator.id.request(); });
  $("body").on("click", ".js-logout", function() { navigator.id.logout(); });
})();
