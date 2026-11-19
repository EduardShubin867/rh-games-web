'use strict';
(() => {
  const current = JSON.parse(document.getElementById('release-config').textContent);
  const banner = document.getElementById('update-banner');
  const dialog = document.getElementById('update-confirm');
  let latest = null;
  let dismissed = '';
  let checked = 0;
  let checking = false;
  async function check() {
    if (checking || document.hidden || Date.now() - checked < 60000) return;
    checking = true;
    checked = Date.now();
    try {
      const response = await fetch('../versions.json', {cache:'no-store', signal:AbortSignal.timeout(12000)});
      if (!response.ok) return;
      const catalog = await response.json();
      const release = catalog.games?.[current.game];
      if (!release || !/^[a-f0-9]{40}$/.test(release.commit) || !/^\d+\.\d+\.\d+$/.test(release.version)) return;
      // Do not interrupt a run or reload without the player's consent.
      if (release.commit !== current.commit && release.commit !== dismissed) {
        latest = release;
        document.getElementById('update-text').textContent = 'Доступна версия '+release.version;
        banner.hidden = false;
      }
    } catch {} finally { checking = false; }
  }
  document.getElementById('show-update').addEventListener('click', () => dialog.showModal());
  document.getElementById('defer-update').addEventListener('click', () => { dismissed = latest.commit; banner.hidden = true; });
  document.getElementById('cancel-update').addEventListener('click', () => dialog.close());
  document.getElementById('apply-update').addEventListener('click', () => {
    if (!latest) return;
    const url = new URL(location.href);
    url.searchParams.set('v', latest.commit);
    url.searchParams.set('reload', String(Date.now()));
    url.searchParams.delete('ui');
    location.replace(url);
  });
  document.addEventListener('visibilitychange', () => { if (!document.hidden) check(); });
  setInterval(check, 15*60*1000);
  check();
})();

