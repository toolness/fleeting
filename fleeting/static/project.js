var Project = (function() {
  var EXPIRY = 10;  // In minutes.

  var repoHome = $('meta[name="repository"]').attr('content');
  var repoName = repoHome && repoHome.split('/')[1];
  var typeaheadMatcher = $.fn.typeahead.Constructor.prototype.matcher;
  var getNextGithubPagePath = function(linkHeader) {
    var NEXT_REGEXP = /<https:\/\/api.github.com\/([^>]*)>;\srel="next"/;
    var match = linkHeader.match(NEXT_REGEXP);

    return match ? '/' + match[1] : null;
  };
  var collectGithubPages = function(path, cb, finalResult) {
    if (!finalResult)
      finalResult = [];
    var req = $.getJSON('https://api.github.com' + path, function(result) {
      finalResult = finalResult.concat(result);
      var linkHeader = req.getResponseHeader('Link');
      if (linkHeader) {
        var nextUrl = getNextGithubPagePath(linkHeader);
        if (nextUrl)
          return collectGithubPages(nextUrl, cb, finalResult);
      }
      return cb(finalResult);
    });
  };
  var getGithubJSON = function(path, cb) {
    var key = 'project:github:' + path;
    var value = lscache.get(key);
    if (value)
      return cb(value);
    collectGithubPages(path, function(value) {
      lscache.set(key, value, EXPIRY);
      cb(value);
    });
  };

  if (repoHome) {
    $(".js-github-user").attr("autocomplete", "off").typeahead({
      matcher: typeaheadMatcher,
      source: function(query, process) {
        getGithubJSON('/repos/' + repoHome + '/forks', function(forks) {
          process(forks.map(function(fork) {
            return fork.owner.login;
          }));
        });
      }
    });
    $(".js-github-branch").attr("autocomplete", "off").typeahead({
      matcher: typeaheadMatcher,
      source: function(query, process) {
        var $el = this.$element;
        var user = $el.prevAll(".js-github-user").first().data("typeahead");
        var username = user.$element.val();

        user.source(username, function(matches) {
          if (matches.indexOf(username) != -1) {
            var path = '/repos/' + username + '/' + repoName + '/branches';
            getGithubJSON(path, function(branches) {
              process(branches.map(function(branch) {
                return branch.name;
              }));
            });
          } else
            process([]);
        });
      }
    });
  }

  return {
    _testing: {
      getGithubJSON: getGithubJSON,
      getNextGithubPagePath: getNextGithubPagePath,
      collectGithubPages: collectGithubPages
    }
  };
})();
