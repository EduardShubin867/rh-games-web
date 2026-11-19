'use strict';

const config = JSON.parse(document.getElementById('game-config').textContent);
const canvas = document.getElementById('canvas');
const player = document.getElementById('player');
const stage = document.getElementById('stage');
const start = document.getElementById('start');
const progress = document.getElementById('progress');
const notice = document.getElementById('notice');
const fullscreen = document.getElementById('fullscreen');
const collapse = document.getElementById('collapse');
const help = document.getElementById('fullscreen-help');
let failed = false;
let launching = false;

function resizeCanvas() {
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.round(stage.clientWidth * ratio);
  const height = Math.round(stage.clientHeight * ratio);
  if (canvas.width !== width) canvas.width = width;
  if (canvas.height !== height) canvas.height = height;
}
new ResizeObserver(resizeCanvas).observe(stage);
resizeCanvas();
document.getElementById('cover').style.backgroundImage = 'linear-gradient(#10221eb0,#10221ef2),url(poster.png)';

config.canvas = canvas;
config.canvasResizePolicy = 0;
config.onProgress = (current, total) => {
  if (total > 0) { progress.max = total; progress.value = current; }
};
const engine = new Engine(config);
const pack = config.mainPack || config.executable + '.pck';

function showFailure(error) {
  console.error(error);
  failed = true;
  notice.textContent = 'Не удалось загрузить игру. Проверьте соединение и обновите страницу.';
  progress.hidden = true;
  start.textContent = 'Обновить';
  start.disabled = false;
}

async function prepareGame() {
  const missing = Engine.getMissingFeatures({threads: false});
  if (missing.length) {
    notice.textContent = 'Браузер не поддерживает: ' + missing.join(', ');
    progress.hidden = true;
    start.textContent = 'Недоступно';
    return;
  }
  try {
    // Finish network work before the gesture that creates Godot's AudioContext.
    await Promise.all([engine.init(config.executable), engine.preloadFile(pack, pack)]);
    progress.hidden = true;
    notice.textContent = '';
    start.textContent = 'Играть';
    start.disabled = false;
    document.documentElement.dataset.gameLoaded = 'true';
  } catch (error) { showFailure(error); }
}

start.addEventListener('click', async () => {
  if (failed) { location.reload(); return; }
  if (launching) return;
  launching = true;
  start.disabled = true;
  try {
    // On iOS, ambient Web Audio follows the ringer switch. Music uses playback.
    if ('audioSession' in navigator) navigator.audioSession.type = 'playback';
    await engine.start({args: ['--main-pack', pack, ...(config.args || [])]});
    document.getElementById('cover').hidden = true;
    canvas.focus();
    document.documentElement.dataset.gameReady = 'true';
  } catch (error) { showFailure(error); }
});
prepareGame();

function isStandalone() {
  return window.matchMedia('(display-mode: standalone)').matches ||
    window.matchMedia('(display-mode: fullscreen)').matches || navigator.standalone === true;
}

function setExpanded(value) {
  player.classList.toggle('expanded', value);
  collapse.hidden = !value;
  if (document.documentElement.dataset.gameReady) canvas.focus();
}

function fullscreenElement() {
  return document.fullscreenElement || document.webkitFullscreenElement;
}

fullscreen.addEventListener('click', async () => {
  if (isStandalone()) { setExpanded(true); return; }
  const request = player.requestFullscreen || player.webkitRequestFullscreen;
  if (!request) { help.showModal(); return; }
  try {
    await request.call(player);
    setExpanded(true);
  } catch (error) {
    // A supported API can still be denied by the browser; keep the fallback usable.
    console.warn('Fullscreen unavailable:', error.message);
    help.showModal();
  }
});

collapse.addEventListener('click', async () => {
  setExpanded(false);
  if (fullscreenElement()) {
    const exit = document.exitFullscreen || document.webkitExitFullscreen;
    await exit.call(document);
  }
  fullscreen.focus();
});
for (const event of ['fullscreenchange', 'webkitfullscreenchange']) {
  document.addEventListener(event, () => {
    if (!fullscreenElement()) setExpanded(false);
  });
}
document.getElementById('expand').addEventListener('click', () => { help.close(); setExpanded(true); });
document.getElementById('close-help').addEventListener('click', () => help.close());
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && player.classList.contains('expanded') && !fullscreenElement()) {
    setExpanded(false);
    fullscreen.focus();
  }
});
