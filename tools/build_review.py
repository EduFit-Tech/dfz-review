# data/changes.json → index.html(개발 항목 목록), data/games.json → 게임 페이지(games/<slug>.html)의 「바뀐 기록」·「수정 요청」 칸을 만든다.
# 사용: python -I tools/build_review.py
#   게임 페이지에는 <!--@HISTORY@--> … <!--@/HISTORY@--> 와 <!--@REQUEST@--> … <!--@/REQUEST@--> 사이가 다시 쓰인다.
# 바탕: HRYoon0/dfz 의 tools/build_review.py. 이 저장소는 공개라서 리뷰어에게 필요한 것만 싣는다 —
#   비공개 저장소의 파일 경로·브랜치·커밋·PR 링크는 자료(games.json)에도 화면에도 두지 않는다.
import datetime, html, json, pathlib, re
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
GAMES = ROOT / "games"
DATA = json.loads((ROOT / "data" / "games.json").read_text(encoding="utf-8"))
CHANGES = json.loads((ROOT / "data" / "changes.json").read_text(encoding="utf-8"))
WEEK = "월화수목금토일"
E = html.escape

# 수정 요청을 받는 Apps Script 웹앱 주소(apps-script/Code.gs를 조직 구글 계정에 배포한 것).
# ★ 비어 있으면 요청 단추 대신 「준비 중」 글이 나온다. 배포한 뒤 data/games.json의 requestUrl에 적는다.
REQUEST_URL = DATA.get("requestUrl", "")
PAGES = DATA["pages"]


def day_label(d):
    y, m, dd = map(int, d.split("-"))
    return f"{y}년 {m}월 {dd}일 ({WEEK[datetime.date(y, m, dd).weekday()]})"


def history_rows(game):
    # 같은 분이면 나중에 적은 기록이 위 — history는 적은 차례로 쌓는다
    rows = [h for _, h in sorted(enumerate(game["history"]), key=lambda x: (x[1]["date"], x[1].get("time", ""), x[0]), reverse=True)]
    return "\n".join(
        f'<li><span class="when">{E(h["date"])} {E(h.get("time", ""))}</span><span>{E(h["text"])}</span></li>'
        for h in rows)


CSS = """
:root{--bg:#202B3D;--surface:#30435A;--line:#46607E;--ink:#F4F8FF;--muted:#CCDCE9;--lime:#D1F58E;
--font:'Pretendard Variable','Pretendard',-apple-system,BlinkMacSystemFont,'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--font);font-weight:450;line-height:1.65;font-size:16px}
main{max-width:1040px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:clamp(28px,4vw,40px);line-height:1.2;margin:0 0 8px;font-weight:800}
h2{font-size:22px;margin:40px 0 12px;font-weight:750;padding-top:8px;border-top:1px solid var(--line)}
h3{font-size:17px;margin:20px 0 8px;font-weight:700;color:var(--lime)}
a{color:var(--lime)}
.lead{color:var(--muted);max-width:46em;margin:0}
ul.log{list-style:none;margin:0;padding:0;display:grid;gap:6px}
ul.log li{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:4px 14px;align-items:baseline;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:9px 14px}
ul.log .when{color:var(--muted);font-variant-numeric:tabular-nums;font-weight:600;white-space:nowrap}
ul.log .game{font-weight:700}
ul.log .note{color:var(--muted);font-size:14px;white-space:nowrap}
.empty{color:var(--muted)}
ul.games li{grid-template-columns:auto minmax(0,1fr) auto;align-items:center}
ul.games .stage{font-size:13px;font-weight:700;border-radius:999px;padding:2px 10px;min-width:6em;text-align:center;white-space:nowrap;background:var(--bg);border:1px solid var(--line);color:var(--muted)}
ul.games .stage.app{background:var(--lime);border-color:var(--lime);color:#13202F}
ul.games .stage.review{border-color:#FFD66B;color:#FFD66B}
ul.games .sub{display:block;color:var(--muted);font-size:14px}
ul.games .req{margin:0;justify-content:flex-end}
.search{display:flex;gap:10px;align-items:center;margin:20px 0 4px}
.search input{flex:1;font:inherit;font-weight:500;color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:10px 14px}
.search input:focus{outline:2px solid var(--lime);outline-offset:1px}
.search .count{color:var(--muted);font-size:14px;white-space:nowrap}
@media (max-width:640px){ul.log li{grid-template-columns:minmax(0,1fr)}ul.games li{grid-template-columns:minmax(0,1fr)}ul.games .req{justify-content:flex-start}}
"""

REQUEST_CSS = """
.req{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:6px}
.req-btn{font:inherit;font-weight:700;font-size:14px;background:var(--bg);color:var(--ink);border:1px solid var(--lime);border-radius:999px;padding:5px 14px;cursor:pointer}
.req-btn:hover{background:var(--lime);color:#13202F}
.req-mark{font-size:14px;font-weight:650;color:#13202F;background:#FFD66B;border-radius:999px;padding:3px 12px}
.req-mark.done{background:var(--lime)}
.req-soon{font-size:14px;color:var(--muted)}
dialog.req-dlg{background:var(--surface);color:var(--ink);border:1px solid var(--line);border-radius:14px;padding:20px;width:min(520px,92vw)}
dialog.req-dlg::backdrop{background:rgba(10,16,26,.6)}
.req-dlg h3{margin:0 0 4px}
.req-dlg label{display:grid;gap:4px;margin-top:12px;font-weight:650;font-size:14px;color:var(--muted)}
.req-dlg .hint{font-weight:450;font-size:13px}
.req-dlg input,.req-dlg textarea{font:inherit;font-weight:450;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
.req-dlg textarea{min-height:130px;resize:vertical}
.req-dlg .row{display:flex;gap:8px;justify-content:flex-end;margin-top:14px;align-items:center}
.req-dlg .row button{font:inherit;font-weight:700;border-radius:10px;padding:8px 16px;cursor:pointer;border:1px solid var(--line);background:var(--bg);color:var(--ink)}
.req-dlg .row button.send{background:var(--lime);color:#13202F;border-color:var(--lime)}
.req-dlg .msg{margin-right:auto;font-size:14px;color:#FFB4A8}
"""

REQUEST_JS = """
(function(){
  var URL_ = %s, PAGES = %s;
  // 응답이 없을 때 「보내는 중」이 영원히 돌지 않게 15초에 끊는다
  function fetchJSON(url, opts, ms){ var c = new AbortController(), t = setTimeout(function(){ c.abort(); }, ms || 15000);
    return fetch(url, Object.assign({}, opts, { signal: c.signal })).then(function(r){ return r.json(); }).finally(function(){ clearTimeout(t); }); }
  function mark(slug, g){
    var el = document.querySelector('.req[data-slug="' + slug + '"] .req-mark'); if (!el || !g || !g.count) return;
    var day = String(g.last || '').slice(0, 10);
    el.textContent = (g.status ? g.status + ' · ' : '의견 있음 · ') + day + (g.count > 1 ? ' (' + g.count + '건)' : '');
    el.title = '마지막 요청 ' + g.last;
    el.classList.toggle('done', !!g.status); el.hidden = false;
  }
  function load(){ fetchJSON(URL_ + '?action=list').then(function(r){ if (r && r.ok) Object.keys(r.games).forEach(function(k){ mark(k, r.games[k]); }); }).catch(function(){}); }
  var dlg = document.getElementById('req-dlg'), form = dlg.querySelector('form'), msg = dlg.querySelector('.msg'), send = dlg.querySelector('.send'), W = form.elements, cur = null;
  document.querySelectorAll('.req-btn').forEach(function(b){ b.addEventListener('click', function(){
    cur = b.closest('.req').dataset; dlg.querySelector('.game').textContent = cur.title; msg.textContent = ''; send.disabled = false; send.textContent = '보내기';
    form.reset(); var n = localStorage.getItem('dfz-req-name'); if (n) W.who.value = n; dlg.showModal(); W.note.focus(); }); });
  dlg.querySelector('.cancel').addEventListener('click', function(){ dlg.close(); });
  form.addEventListener('submit', function(e){
    e.preventDefault(); if (!cur) return;
    var text = W.note.value.trim(); if (text.length < 2) { msg.textContent = '의견을 적어 주세요.'; return; }
    send.disabled = true; send.textContent = '보내는 중…'; msg.textContent = '';
    localStorage.setItem('dfz-req-name', W.who.value.trim());
    // text/plain — 브라우저가 사전 요청(OPTIONS)을 보내지 않게(Apps Script는 그것을 받지 못한다)
    fetchJSON(URL_, { method: 'POST', headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: JSON.stringify({ slug: cur.slug, title: cur.title, page: PAGES + cur.page, name: W.who.value.trim(), text: text }) })
      .then(function(r){
        if (!r || !r.ok) throw new Error(r && r.error || 'fail');
        dlg.close(); load();
        mark(cur.slug, { count: 1, last: r.at, status: '' });
      })
      .catch(function(err){ send.disabled = false; send.textContent = '다시 보내기';
        msg.textContent = String(err.message) === 'rate-limit' ? '요청이 몰렸어요. 10분 뒤 다시 보내 주세요.' : '보내지 못했어요. 다시 보내 주세요.'; });
  });
  load();
})();
""" % (json.dumps(REQUEST_URL), json.dumps(PAGES))

# ★ 이름 칸에 실명을 적지 않게 안내한다 — 시트에 쌓이는 값이다.
REQUEST_DIALOG = """<dialog class="req-dlg" id="req-dlg" aria-labelledby="req-h">
<form method="dialog">
<h3 id="req-h">의견 보내기</h3>
<div class="game" style="font-weight:700"></div>
<label>보내는 사람(선택)<span class="hint">별명이나 소속만 적어 주세요. 실명·연락처는 적지 마세요.</span><input name="who" maxlength="40" autocomplete="off"></label>
<label>의견<textarea name="note" maxlength="1000" required placeholder="좋은 점, 고칠 점, 궁금한 점을 적어 주세요"></textarea></label>
<div class="row"><span class="msg" role="status"></span><button type="button" class="cancel">취소</button><button type="submit" class="send">보내기</button></div>
</form>
</dialog>"""

SOON = '<span class="req-soon">의견 받기는 준비 중입니다.</span>'


def req_div(g, label, page, style=""):
    """요청 단추 한 벌. 받을 주소가 아직 없으면 단추 대신 「준비 중」."""
    inner = (f'<span class="req-mark" hidden></span><button type="button" class="req-btn">{label}</button>' if REQUEST_URL else SOON)
    return (f'<div class="req" data-slug="{E(g["slug"])}" data-title="{E(g["title"])}" data-page="{E(page)}"{style}>{inner}</div>')


def page_of(g):
    return "games/" + g["slug"] + ".html"


def change_card(c, area_name):
    """개발 항목 한 칸 — 쉬운 요약, 봐 주셨으면 하는 것, 체험판 링크, 의견 보내기."""
    label, cls = ("들어감", "app") if c["state"] == "done" else ("검토 중", "review")
    slug = f'c{c["id"]}'
    ask = f'<p class="ask"><b>봐 주셨으면 하는 것</b> {E(c["ask"])}</p>' if c.get("ask") else ""
    demo = f'<a class="demo" href="games/{E(c["game"])}.html">체험판 해 보기</a>' if c.get("game") else ""
    q = " ".join([c["title"], c["summary"], area_name, label, str(c["id"])]).lower()
    g = {"slug": slug, "title": c["title"]}
    return (f'<li class="chg" id="{slug}" data-area="{E(c["area"])}" data-state="{cls}" data-q="{E(q)}">'
            f'<div class="top"><span class="stage {cls}">{label}</span><span class="area">{E(area_name)}</span>'
            f'<span class="when">{E(c["date"])}</span><span class="no">항목 {c["id"]}</span></div>'
            f'<h3>{E(c["title"])}</h3><p>{E(c["summary"])}</p>{ask}'
            f'<div class="foot">{demo}{req_div(g, "의견 보내기", "#" + slug)}</div></li>')


FILTER_JS = """
(function(){
  var q = document.getElementById('q'), count = document.getElementById('q-count'), empty = document.getElementById('q-empty');
  var items = [].slice.call(document.querySelectorAll('li.chg')), area = '', state = '';
  function run(){
    var words = q.value.toLowerCase().split(/\\s+/).filter(Boolean), n = 0;
    items.forEach(function(li){
      var ok = (!area || li.dataset.area === area) && (!state || li.dataset.state === state) && words.every(function(w){ return li.dataset.q.indexOf(w) >= 0; });
      li.hidden = !ok; if (ok) n++; });
    count.textContent = n + '개'; empty.hidden = n > 0;
  }
  document.querySelectorAll('.chips button').forEach(function(b){ b.addEventListener('click', function(){
    var grp = b.parentNode; grp.querySelectorAll('button').forEach(function(x){ x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
    if (grp.dataset.kind === 'area') area = b.dataset.v; else state = b.dataset.v; run(); }); });
  q.addEventListener('input', run); run();
})();
"""

INDEX_CSS = """
ul.changes{list-style:none;margin:16px 0 0;padding:0;display:grid;gap:10px}
li.chg{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
li.chg[hidden]{display:none}
li.chg .top{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center;font-size:14px;color:var(--muted)}
li.chg .stage{font-size:13px;font-weight:700;border-radius:999px;padding:2px 10px;background:var(--bg);border:1px solid var(--line)}
li.chg .stage.app{background:var(--lime);border-color:var(--lime);color:#13202F}
li.chg .stage.review{border-color:#FFD66B;color:#FFD66B}
li.chg .area{font-weight:700;color:var(--ink)}
li.chg .when{font-variant-numeric:tabular-nums}
li.chg h3{margin:8px 0 4px;font-size:19px;color:var(--ink)}
li.chg p{margin:0;max-width:52em}
li.chg p.ask{margin-top:8px;color:var(--muted)}
li.chg p.ask b{color:var(--lime);margin-right:6px}
li.chg .foot{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:10px}
li.chg .foot .req{margin:0}
li.chg a.demo{font-weight:700;font-size:14px;border:1px solid var(--line);border-radius:999px;padding:5px 14px;text-decoration:none;background:var(--bg)}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.chips button{font:inherit;font-size:14px;font-weight:650;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:999px;padding:5px 14px;cursor:pointer}
.chips button[aria-pressed=true]{background:var(--lime);border-color:var(--lime);color:#13202F}
"""


def build_index():
    areas = {a["key"]: a["name"] for a in CHANGES["areas"]}
    items = sorted(CHANGES["changes"], key=lambda c: (c["date"], c["id"]), reverse=True)
    cards = "\n".join(change_card(c, areas[c["area"]]) for c in items)
    used = [a for a in CHANGES["areas"] if any(c["area"] == a["key"] for c in items)]
    area_chips = '<button type="button" data-v="" aria-pressed="true">모든 분야</button>' + "".join(
        f'<button type="button" data-v="{E(a["key"])}" aria-pressed="false">{E(a["name"])} {sum(1 for c in items if c["area"] == a["key"])}</button>' for a in used)
    n_review = sum(1 for c in items if c["state"] != "done")
    state_chips = (f'<button type="button" data-v="" aria-pressed="true">전체 {len(items)}</button>'
                   f'<button type="button" data-v="review" aria-pressed="false">검토 중 {n_review}</button>'
                   f'<button type="button" data-v="app" aria-pressed="false">들어감 {len(items) - n_review}</button>')
    page = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>디지털 핏 존 개발 리뷰</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<style>{CSS}{INDEX_CSS}{REQUEST_CSS}</style>
</head>
<body>
<main>
<h1>디지털 핏 존 개발 리뷰</h1>
<p class="lead">디지털 핏 존 팀이 만들고 고치는 것을 보고 의견을 주시는 곳입니다. 항목마다 무엇이 달라지는지 적었고, 게임은 브라우저에서 해 보는 체험판이 있습니다. 「검토 중」은 아직 앱에 들어가지 않은 것이고 「들어감」은 이미 들어간 것입니다. 의견이 있으면 항목의 「의견 보내기」를 눌러 주세요. 보내신 내용은 개발 팀만 보고, 이 페이지에는 의견이 들어온 날짜와 건수만 표시됩니다. 체험판은 앱과 같은 규칙으로 따로 만든 것이라 그림과 조작이 실제 앱과 조금 다를 수 있습니다.</p>
<div class="search"><input type="search" id="q" placeholder="찾기 — 게임 이름, 낱말" aria-label="항목 찾기"><span class="count" id="q-count"></span></div>
<div class="chips" data-kind="area">{area_chips}</div>
<div class="chips" data-kind="state">{state_chips}</div>
<ul class="changes">
{cards}
</ul>
<p class="empty" id="q-empty" hidden>맞는 항목이 없습니다.</p>
</main>
{REQUEST_DIALOG if REQUEST_URL else ''}
{f'<script>{REQUEST_JS}</script>' if REQUEST_URL else ''}
<script>{FILTER_JS}</script>
</body>
</html>
"""
    (ROOT / "index.html").write_text(page, encoding="utf-8", newline="\n")


def request_block(g):
    """게임 페이지 머리의 「수정 요청」 — 목록과 같은 웹앱·같은 창."""
    tail = f'{REQUEST_DIALOG}\n<script>{REQUEST_JS}</script>\n' if REQUEST_URL else ""
    return (f'<!--@REQUEST@-->\n<style>{REQUEST_CSS}</style>\n'
            f'{req_div(g, "이 게임에 의견 보내기", page_of(g), " style=" + chr(34) + "margin:14px 0 0" + chr(34))}\n'
            f'{tail}<!--@/REQUEST@-->')


def build_game_pages():
    pat = re.compile(r"<!--@HISTORY@-->.*?<!--@/HISTORY@-->", re.S)
    req = re.compile(r"<!--@REQUEST@-->.*?<!--@/REQUEST@-->", re.S)
    for g in DATA["games"]:
        p = GAMES / (g["slug"] + ".html")
        s = p.read_text(encoding="utf-8")
        for name, rx in (("HISTORY", pat), ("REQUEST", req)):
            if not rx.search(s):
                raise SystemExit(f"{p.name}에 <!--@{name}@--> 칸이 없다")
        s = pat.sub(lambda _: f'<!--@HISTORY@-->\n<ul class="log">\n{history_rows(g)}\n</ul>\n<!--@/HISTORY@-->', s)
        s = req.sub(lambda _: request_block(g), s)
        p.write_text(s, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")   # 윈도 기본 터미널(cp949)에서 「—」에 죽지 않게
    build_game_pages()
    build_index()
    print("index.html 과 게임 페이지", len(DATA["games"]), "개를 다시 썼다", "(요청 받기 켜짐)" if REQUEST_URL else "(요청 받기 주소 없음 — 준비 중으로 표시)")
