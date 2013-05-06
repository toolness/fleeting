"use strict";

var Project = (function() {
  var EXPIRY = 10;               // In minutes.

  var typeaheadMatcher = $.fn.typeahead.Constructor.prototype.matcher;
  var ghFork = '[data-github-fork]';
  var ghBranch = '[data-github-branch]';
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

  $(document).on('focus.github.data-api', ghFork, function(e) {
    var $this = $(this);

    if ($this.data('typeahead')) return;

    var repoHome = $(this).attr("data-github-fork");
    var repoName = repoHome.split('/')[1];

    $this.attr("data-github-repo-name", repoName);
    $this.attr("autocomplete", "off").typeahead({
      matcher: typeaheadMatcher,
      source: function(query, process) {
        getGithubJSON('/repos/' + repoHome + '/forks', function(forks) {
          process(forks.map(function(fork) {
            return fork.owner.login;
          }));
        });
      }      
    });
  });

  $(document).on('focus.github.data-api', ghBranch, function(e) {
    var $this = $(this);

    if ($this.data('typeahead')) return;

    var fork = $this.prevAll(ghFork).first().data("typeahead");

    if (!fork) return;

    var repoName = fork.$element.attr("data-github-repo-name");

    $this.attr("autocomplete", "off").typeahead({
      matcher: typeaheadMatcher,
      source: function(query, process) {
        var username = fork.$element.val();

        fork.source(username, function(matches) {
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
  });

  $(window).on('load', function() {
    $('[data-refresh-url]').each(function() {
      var $this = $(this);
      var url = $this.attr('data-refresh-url');
      var interval = parseInt($this.attr('data-refresh-seconds')) * 1000;

      setInterval(function() { $this.load(url); }, interval);
    });
  });

  return {
    _testing: {
      getGithubJSON: getGithubJSON,
      getNextGithubPagePath: getNextGithubPagePath,
      collectGithubPages: collectGithubPages
    }
  };
})();
