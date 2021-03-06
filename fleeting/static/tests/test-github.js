(function() {
  module("github");

  test("getNextGithubPagePath() return path when one exists", function() {
    var linkHeader = '<https://api.github.com/repositories/1726649/' +
      'forks?page=2>; rel="next", <https://api.github.com/repositories/' +
      '1726649/forks?page=4>; rel="last"';
    equal(Github._testing.getNextGithubPagePath(linkHeader),
          '/repositories/1726649/forks?page=2');
  });

  test("getNextGithubPagePath() returns null if no path", function() {
    var linkHeader = '<https://api.github.com/repositories/1726649/' +
      'forks?page=2>; rel="prev"';
    equal(Github._testing.getNextGithubPagePath(linkHeader), null);
  });
})();
