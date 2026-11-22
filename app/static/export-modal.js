(function () {
  var dialog = document.getElementById('export-modal');
  if (!dialog) return;

  var content = dialog.querySelector('[data-export-content]');
  var loading = dialog.querySelector('[data-export-loading]');
  var trigger = null;
  var request = null;
  var printFrame = null;
  var printTimer = null;

  function removePrintFrame() {
    if (printTimer) {
      window.clearTimeout(printTimer);
      printTimer = null;
    }
    if (printFrame && printFrame.parentNode) printFrame.parentNode.removeChild(printFrame);
    printFrame = null;
  }

  function printWithoutNewTab(url) {
    removePrintFrame();
    var frame = document.createElement('iframe');
    frame.setAttribute('aria-hidden', 'true');
    frame.setAttribute('tabindex', '-1');
    frame.style.cssText = 'position:fixed;left:-10000px;top:0;width:1024px;height:768px;border:0;';
    frame.addEventListener('load', function () {
      try {
        frame.contentWindow.addEventListener('afterprint', removePrintFrame);
        frame.contentWindow.focus();
      } catch (error) {
        removePrintFrame();
      }
    });
    frame.src = url;
    printFrame = frame;
    document.body.appendChild(frame);
    printTimer = window.setTimeout(removePrintFrame, 300000);
  }

  function showLoading() {
    content.innerHTML = '';
    loading.hidden = false;
  }

  function open(url, triggerElement) {
    trigger = triggerElement;
    if (typeof dialog.showModal === 'function') {
      if (!dialog.open) dialog.showModal();
    } else {
      dialog.setAttribute('open', '');
    }
    document.body.classList.add('export-modal-open');
    showLoading();

    if (request) request.abort();
    request = new AbortController();

    fetch(url, { signal: request.signal })
      .then(function (response) {
        if (!response.ok) throw new Error('Preview request failed');
        return response.text();
      })
      .then(function (html) {
        content.innerHTML = html;
        loading.hidden = true;
        var title = content.querySelector('[data-export-title]');
        if (title) title.focus({ preventScroll: true });
      })
      .catch(function (error) {
        if (error.name === 'AbortError') return;
        content.innerHTML = '<div class="export-modal-error"><p>Could not load the export preview. Please try again.</p><button type="button" class="button" data-export-close>Close</button></div>';
        loading.hidden = true;
      });
  }

  function close() {
    if (request) {
      request.abort();
      request = null;
    }
    if (typeof dialog.close === 'function' && dialog.open) {
      dialog.close();
    } else {
      dialog.removeAttribute('open');
      cleanup();
    }
  }

  function cleanup() {
    document.body.classList.remove('export-modal-open');
    content.innerHTML = '';
    loading.hidden = false;
    if (trigger) trigger.focus({ preventScroll: true });
    trigger = null;
  }

  document.addEventListener('click', function (event) {
    var triggerElement = event.target.closest('[data-export-modal]');
    if (triggerElement) {
      event.preventDefault();
      open(triggerElement.getAttribute('data-export-modal-url') || triggerElement.getAttribute('href'), triggerElement);
      return;
    }

    var closeElement = event.target.closest('[data-export-close]');
    if (closeElement && dialog.contains(closeElement)) {
      event.preventDefault();
      close();
      return;
    }

    var printElement = event.target.closest('[data-export-print]');
    if (printElement && dialog.contains(printElement)) {
      event.preventDefault();
      var printUrl = printElement.getAttribute('data-print-url');
      if (!printUrl) return;
      printWithoutNewTab(printUrl);
    }
  });

  dialog.addEventListener('click', function (event) {
    if (event.target === dialog) close();
  });

  dialog.addEventListener('close', cleanup);
})();
