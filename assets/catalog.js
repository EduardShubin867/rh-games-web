'use strict';
(() => {
  const root = new URL(document.documentElement.dataset.root, location.href);
  // S3 origin keeps browser CORS independent of the CDN cache's Origin handling.
  const MANIFEST_ORIGIN = 'https://a0c426f1-b96f4d72-6fef-4054-b115-caf918644aa6.s3.twcstorage.ru';
  const CDN = 'https://m9a4xhtu4l.cdn.twcstorage.ru';
  const slugs = ['lovec-suiko', 'hk-in-a-row'];
  const stableVersion = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;
  async function json(url) {
    const response = await fetch(url, {cache: 'no-store', signal: AbortSignal.timeout(12000)});
    if (!response.ok) throw new Error('Release unavailable');
    return response.json();
  }
  json(new URL('versions.json', root)).then(catalog => {
    for (const slug of slugs) {
      const release = catalog.games?.[slug];
      if (!release || !stableVersion.test(release.version) || !/^[a-f0-9]{40}$/.test(release.commit)) return;
    }
    for (const slug of slugs) {
      const release = catalog.games[slug];
      document.querySelectorAll('[data-version="'+slug+'"]').forEach(node => { node.textContent = 'v' + release.version; });
      document.querySelectorAll('[data-play="'+slug+'"]').forEach(link => {
        const url = new URL(slug+'/', root);
        url.searchParams.set('v', release.commit);
        const revision = document.querySelector('script[src*="catalog.js"]').src.split('?')[1];
        if (revision) url.searchParams.set('ui', new URLSearchParams(revision).get('v'));
        link.href = url;
      });
    }
  }).catch(() => {}); // Server-rendered pinned links remain usable offline.

  async function nativeDownloads(slug) {
    try {
      const release = await json(MANIFEST_ORIGIN+'/updates/'+slug+'/stable.json');
      if (release.schema !== 1 || release.game !== slug || release.channel !== 'stable' || !stableVersion.test(release.version)) throw new Error('Invalid release');
      for (const platform of ['android', 'windows']) {
        const file = release.downloads?.[platform];
        const url = new URL(file?.url);
        const prefix = '/releases/'+slug+'/'+release.version+'/';
        if (url.origin !== CDN || !url.pathname.startsWith(prefix) || url.username || url.password || url.search || url.hash ||
            /%|\\|\.\./.test(file.url) || !url.pathname.endsWith(platform === 'android' ? '.apk' : '.zip') ||
            !Number.isSafeInteger(file.bytes) || file.bytes <= 0 || !/^[a-f0-9]{64}$/.test(file.sha256)) throw new Error('Invalid download');
      }
      for (const platform of ['android', 'windows']) {
        const file = release.downloads[platform];
        document.querySelectorAll('[data-download="'+slug+':'+platform+'"]').forEach(link => {
          link.href = file.url;
          link.removeAttribute('aria-disabled');
          link.removeAttribute('tabindex');
          link.title = 'Версия '+release.version+' · SHA-256: '+file.sha256;
        });
      }
      document.querySelectorAll('[data-native-version="'+slug+'"]').forEach(node => { node.textContent = 'v'+release.version; });
      document.querySelectorAll('[data-size="'+slug+'"]').forEach(node => { node.textContent = (release.downloads.android.bytes/1048576).toLocaleString('ru-RU',{maximumFractionDigits:1})+' МБ'; });
      document.querySelectorAll('[data-download-status="'+slug+'"]').forEach(node => { node.textContent = 'Для Android и Windows доступна версия '+release.version; });
    } catch {
      document.querySelectorAll('[data-download-status="'+slug+'"]').forEach(node => { node.textContent = 'Загрузка приложения пока недоступна. Можно играть в браузере.'; });
      document.querySelectorAll('[data-native-version="'+slug+'"],[data-size="'+slug+'"]').forEach(node => { node.textContent = 'Пока недоступно'; });
    }
  }
  for (const slug of slugs) {
    if (document.querySelector('[data-download^="'+slug+':"]')) nativeDownloads(slug);
  }
  const dialog = document.querySelector('.gallery-dialog');
  if (dialog) {
    document.querySelectorAll('[data-shot]').forEach(button => button.addEventListener('click', () => {
      dialog.querySelector('img').src = button.dataset.shot;
      dialog.querySelector('img').alt = button.querySelector('img').alt;
      dialog.showModal();
    }));
    dialog.querySelector('button').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  }
})();

