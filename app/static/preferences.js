(function () {
  var COOKIE = 'dats2_prefs';
  var MAX_AGE = 15552000;
  var DEFAULTS = { reduce_motion: false, hide_hints: false };

  function readPreferences() {
    var prefix = COOKIE + '=';
    var part = document.cookie.split('; ').find(function (item) {
      return item.indexOf(prefix) === 0;
    });
    if (!part) return Object.assign({}, DEFAULTS);
    try {
      var parsed = JSON.parse(decodeURIComponent(part.slice(prefix.length)));
      if (!parsed || typeof parsed !== 'object') return Object.assign({}, DEFAULTS);
      return {
        reduce_motion: parsed.reduce_motion === true,
        hide_hints: parsed.hide_hints === true
      };
    } catch (error) {
      return Object.assign({}, DEFAULTS);
    }
  }

  function writePreferences(preferences) {
    var value = encodeURIComponent(JSON.stringify({
      reduce_motion: preferences.reduce_motion === true,
      hide_hints: preferences.hide_hints === true
    }));
    var secure = window.location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = COOKIE + '=' + value + '; Max-Age=' + MAX_AGE + '; Path=/; SameSite=Lax' + secure;
  }

  function clearPreferences() {
    var secure = window.location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = COOKIE + '=; Max-Age=0; Path=/; SameSite=Lax' + secure;
  }

  function applyPreferences(preferences) {
    document.documentElement.setAttribute('data-reduce-motion', preferences.reduce_motion ? 'true' : 'false');
    document.documentElement.setAttribute('data-hide-hints', preferences.hide_hints ? 'true' : 'false');
  }

  function syncForm(reduceMotion, showHints, preferences) {
    if (reduceMotion) reduceMotion.checked = preferences.reduce_motion;
    if (showHints) showHints.checked = !preferences.hide_hints;
  }

  function setDialogOpen(open) {
    document.body.classList.toggle('preferences-open', open);
  }

  function openDialog(dialog) {
    if (typeof dialog.showModal === 'function') {
      dialog.showModal();
    } else {
      dialog.setAttribute('open', '');
    }
    setDialogOpen(true);
  }

  function closeDialog(dialog) {
    if (typeof dialog.close === 'function') {
      dialog.close();
    } else {
      dialog.removeAttribute('open');
    }
    setDialogOpen(false);
  }

  function addHintDismissButtons() {
    document.querySelectorAll('.table-scroll-hint').forEach(function (hint) {
      if (hint.querySelector('[data-hint-dismiss]')) return;
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'hint-dismiss';
      button.setAttribute('data-hint-dismiss', '');
      button.setAttribute('aria-label', 'Hide table scroll hint');
      button.textContent = 'Hide';
      button.addEventListener('click', function () {
        var preferences = readPreferences();
        preferences.hide_hints = true;
        writePreferences(preferences);
        applyPreferences(preferences);
      });
      hint.appendChild(button);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var dialog = document.getElementById('preferences-dialog');
    if (!dialog) return;

    var reduceMotion = dialog.querySelector('[data-pref-reduce-motion]');
    var showHints = dialog.querySelector('[data-pref-show-hints]');
    var openButtons = document.querySelectorAll('[data-preferences-open]');
    var closeButton = dialog.querySelector('[data-preferences-close]');
    var saveButton = dialog.querySelector('[data-preferences-save]');
    var resetButton = dialog.querySelector('[data-preferences-reset]');
    var preferences = readPreferences();

    syncForm(reduceMotion, showHints, preferences);
    addHintDismissButtons();

    openButtons.forEach(function (button) {
      button.addEventListener('click', function () {
        preferences = readPreferences();
        syncForm(reduceMotion, showHints, preferences);
        openDialog(dialog);
      });
    });

    if (closeButton) {
      closeButton.addEventListener('click', function () {
        closeDialog(dialog);
      });
    }

    if (saveButton) {
      saveButton.addEventListener('click', function () {
        preferences = {
          reduce_motion: !!(reduceMotion && reduceMotion.checked),
          hide_hints: !!(showHints && !showHints.checked)
        };
        writePreferences(preferences);
        applyPreferences(preferences);
        closeDialog(dialog);
      });
    }

    if (resetButton) {
      resetButton.addEventListener('click', function () {
        clearPreferences();
        preferences = Object.assign({}, DEFAULTS);
        applyPreferences(preferences);
        syncForm(reduceMotion, showHints, preferences);
        closeDialog(dialog);
      });
    }

    dialog.addEventListener('click', function (event) {
      if (event.target === dialog) closeDialog(dialog);
    });
    dialog.addEventListener('close', function () {
      setDialogOpen(false);
    });
  });
})();
