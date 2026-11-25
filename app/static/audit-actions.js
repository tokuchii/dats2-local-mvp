(function () {
  document.addEventListener('DOMContentLoaded', function () {
    var dialog = document.getElementById('audit-action-dialog');
    var form = document.getElementById('audit-action-form');
    if (!dialog || !form) return;

    var warning = dialog.querySelector('#audit-action-warning');
    var triggers = document.querySelectorAll('[data-audit-action]');

    function setOpen(open) {
      document.body.classList.toggle('audit-action-open', open);
    }

    function closeDialog() {
      if (typeof dialog.close === 'function') {
        dialog.close();
      } else {
        dialog.removeAttribute('open');
      }
      setOpen(false);
    }

    function openDialog(trigger) {
      form.setAttribute('action', trigger.dataset.actionUrl);
      warning.textContent = trigger.dataset.actionWarning || '';
      if (typeof dialog.showModal === 'function') {
        dialog.showModal();
      } else {
        dialog.setAttribute('open', '');
      }
      setOpen(true);
    }

    triggers.forEach(function (trigger) {
      trigger.addEventListener('click', function () {
        openDialog(trigger);
      });
    });

    dialog.querySelectorAll('[data-audit-cancel]').forEach(function (button) {
      button.addEventListener('click', closeDialog);
    });

    dialog.addEventListener('click', function (event) {
      if (event.target === dialog) closeDialog();
    });
    dialog.addEventListener('close', function () {
      setOpen(false);
    });
  });
})();
