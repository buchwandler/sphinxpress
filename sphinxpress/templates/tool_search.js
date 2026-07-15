(function () {
  "use strict";

  function initForm(form) {
    var input = form.querySelector(".tool-search-input");
    var results = form.querySelector(".tool-search-results");
    var navList = form.parentElement
      ? form.parentElement.querySelector(".tool-nav-list")
      : null;
    if (!input || !results) {
      return;
    }
    var emptyText = form.getAttribute("data-search-empty") || "No matches.";
    var indexUrl = form.getAttribute("data-search-index");
    if (!indexUrl) {
      hideForm();
      return;
    }

    var indexEntries = null;
    var indexError = false;
    var pendingQuery = null;

    function hideForm() {
      form.style.display = "none";
    }

    function escapeHtml(value) {
      return value
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function showEmpty() {
      results.innerHTML =
        '<p class="tool-search-empty">' + escapeHtml(emptyText) + "</p>";
      results.hidden = false;
      if (navList) {
        navList.hidden = true;
      }
    }

    function clearResults() {
      results.innerHTML = "";
      results.hidden = true;
      if (navList) {
        navList.hidden = false;
      }
    }

    function renderResults(entries, tokens) {
      if (!entries.length) {
        showEmpty();
        return;
      }
      var html = entries
        .map(function (entry) {
          var snippetHtml = renderSnippet(entry, tokens);
          var href = entry.url + "#sphinxpress-search-hit";
          return (
            '<li class="tool-search-result">' +
            '<a href="' +
            escapeHtml(href) +
            '">' +
            '<p class="tool-search-result-title">' +
            escapeHtml(entry.title) +
            "</p>" +
            '<p class="tool-search-result-snippet">' +
            snippetHtml +
            "</p>" +
            "</a>" +
            "</li>"
          );
        })
        .join("");
      results.innerHTML = html;
      results.hidden = false;
      if (navList) {
        navList.hidden = true;
      }
    }

    function renderSnippet(entry, tokens) {
      var source = entry.snippet || "";
      if (!source) {
        return "";
      }
      var lower = source.toLowerCase();
      var firstToken = tokens[0] || "";
      var idx = lower.indexOf(firstToken);
      if (idx < 0) {
        return escapeHtml(source);
      }
      var before = source.slice(0, idx);
      var match = source.slice(idx, idx + firstToken.length);
      var after = source.slice(idx + firstToken.length);
      return (
        escapeHtml(before) +
        "<mark>" +
        escapeHtml(match) +
        "</mark>" +
        escapeHtml(after)
      );
    }

    function runQuery(query) {
      if (!indexEntries) {
        return;
      }
      var tokens = query
        .toLowerCase()
        .split(/\s+/)
        .filter(function (token) {
          return token.length > 0;
        });
      if (!tokens.length) {
        clearResults();
        return;
      }
      var hits = [];
      for (var i = 0; i < indexEntries.length; i += 1) {
        var entry = indexEntries[i];
        if (!entry.sections || !entry.sections.length) {
          continue;
        }
        var matched = true;
        var score = 0;
        for (var t = 0; t < tokens.length; t += 1) {
          var token = tokens[t];
          var found = false;
          var tokenScore = 0;
          for (var s = 0; s < entry.sections.length; s += 1) {
            var section = entry.sections[s];
            var lowerText = section.lower || "";
            if (!lowerText) {
              continue;
            }
            var from = 0;
            while (from <= lowerText.length) {
              var foundAt = lowerText.indexOf(token, from);
              if (foundAt < 0) {
                break;
              }
              tokenScore += 1;
              from = foundAt + token.length;
            }
            if (tokenScore > 0) {
              found = true;
            }
          }
          if (!found) {
            matched = false;
            break;
          }
          score += tokenScore;
        }
        if (matched) {
          hits.push({ entry: entry, score: score });
        }
      }
      hits.sort(function (a, b) {
        return b.score - a.score;
      });
      var top = hits.slice(0, 20).map(function (hit) {
        return hit.entry;
      });
      renderResults(top, tokens);
    }

    function handleInput() {
      var query = input.value || "";
      if (!query.trim()) {
        clearResults();
        pendingQuery = null;
        return;
      }
      if (indexError) {
        hideForm();
        return;
      }
      if (indexEntries) {
        runQuery(query);
      } else {
        pendingQuery = query;
      }
    }

    input.addEventListener("input", handleInput);

    fetch(indexUrl, { credentials: "same-origin" })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("HTTP " + response.status);
        }
        return response.json();
      })
      .then(function (payload) {
        if (
          !payload ||
          !Array.isArray(payload.entries) ||
          payload.entries.length === 0
        ) {
          hideForm();
          return;
        }
        indexEntries = payload.entries;
        if (pendingQuery) {
          runQuery(pendingQuery);
        }
      })
      .catch(function () {
        indexError = true;
        if (input.value && input.value.trim()) {
          hideForm();
        } else {
          hideForm();
        }
      });
  }

  function init() {
    var forms = document.querySelectorAll("form.tool-search");
    for (var i = 0; i < forms.length; i += 1) {
      initForm(forms[i]);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
