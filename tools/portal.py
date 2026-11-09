"""Render the public catalog and game details from factual local content."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def footer(prefix):
    return f'''<footer class="site-footer"><div class="container footer-inner"><div class="footer-top"><a class="brand" href="{prefix}" aria-label="RH Games — главная"><span class="brand-mark"><img src="{prefix}assets/icons/brand-small.svg" alt=""></span>RH GAMES</a><nav class="footer-links" aria-label="Внизу страницы"><a href="{prefix}#games">Игры</a><a href="{prefix}#install">Установка</a></nav></div><div class="footer-bottom"><p>© 2026 Рита Хоффман</p><a href="https://games.rita-hoffman.ru">games.rita-hoffman.ru</a></div></div></footer>'''


def card(slug, game, version, prefix):
    e = html.escape
    return f'''<article class="card"><a class="art-link" href="{prefix}{slug}/about.html" aria-label="Об игре «{e(game['title'])}»"><img src="{prefix}assets/games/{e(game['cover'])}" alt="Иллюстрация из игры «{e(game['title'])}»" width="584" height="320" loading="lazy"></a><div class="card-body"><div class="card-title"><h3><a href="{prefix}{slug}/about.html">{e(game['title'])}</a></h3><span class="chip" data-version="{slug}">v{version}</span></div><p class="card-description">{e(game['short'])}</p><p class="meta">{e(game['genre'])} · В браузере и на устройстве</p><div class="button-row"><a class="button" href="{prefix}{slug}/" data-play="{slug}"><img src="{prefix}assets/icons/play.svg" alt="">Играть в браузере</a><a class="button button-outline" data-download="{slug}:android" aria-disabled="true" tabindex="-1"><img src="{prefix}assets/icons/download.svg" alt=""><span>Скачать APK</span></a></div><a class="details-link" href="{prefix}{slug}/about.html">Об игре и скриншоты →</a><p class="meta" data-download-status="{slug}" role="status">Проверяем доступность загрузок…</p></div></article>'''


def render_portal(destination, catalog, revision):
    content = json.loads((ROOT / "catalog-content.json").read_text(encoding="utf-8"))
    if set(content) != set(catalog["games"]):
        raise ValueError("Portal content must describe every pinned game")
    page = (ROOT / "site/index.html").read_text(encoding="utf-8")
    cards = "".join(card(slug, game, catalog["games"][slug]["version"], "") for slug, game in content.items())
    page = page.replace("__GAME_CARDS__", cards).replace("__FOOTER__", footer("./"))
    page = page.replace("__ASSET_VERSION__", revision)
    (destination / "index.html").write_text(page, encoding="utf-8")
    for slug, game in content.items():
        template = (ROOT / "templates/details.html").read_text(encoding="utf-8")
        shots = "".join(f'<button class="shot" type="button" data-shot="../assets/games/{html.escape(file)}" aria-label="Увеличить: {html.escape(label)}"><img src="../assets/games/{html.escape(file)}" alt="{html.escape(label)}" width="384" height="288" loading="lazy"></button>' for file, label in game["shots"])
        about = "".join("<p>" + html.escape(p) + "</p>" for p in game["about"])
        features = "".join('<li><img src="../assets/icons/check.svg" alt="">' + html.escape(p) + "</li>" for p in game["features"])
        other = next(key for key in content if key != slug)
        values = {"TITLE": game["title"], "SUBTITLE": game["subtitle"], "GENRE": game["genre"],
                  "DESCRIPTION": game["short"], "SLUG": slug, "VERSION": catalog["games"][slug]["version"],
                  "COVER": game["cover"], "ASSET_VERSION": revision}
        for key, value in values.items():
            template = template.replace("__" + key + "__", html.escape(value))
        template = template.replace("__SCREENSHOTS__", shots).replace("__ABOUT__", about).replace("__FEATURES__", features)
        template = template.replace("__OTHER_GAME__", card(other, content[other], catalog["games"][other]["version"], "../"))
        template = template.replace("__FOOTER__", footer("../"))
        folder = destination / slug
        folder.mkdir(exist_ok=True)
        (folder / "about.html").write_text(template, encoding="utf-8")
    # Decorate only actual play links; detail links must keep their destination.
    for path in [destination / "index.html", *(destination / slug / "about.html" for slug in content)]:
        page = path.read_text(encoding="utf-8")
        prefix = "" if path.parent == destination else "../"
        for slug, entry in catalog["games"].items():
            play_path = "./" if path.parent.name == slug else prefix + slug + "/"
            page = page.replace(f'href="{play_path}" data-play="{slug}"', f'href="{play_path}?v={entry["commit"]}&amp;ui={revision}" data-play="{slug}"')
        if "__" in page:
            raise ValueError("Unresolved portal template token in " + str(path))
        path.write_text(page, encoding="utf-8")

