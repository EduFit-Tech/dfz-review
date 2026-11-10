/**
 * 디지털 핏 존 개발 리뷰(https://edufit-tech.github.io/dfz-review/)의 「의견 보내기」를 구글 시트에 받는다.
 * 바탕: HRYoon0/dfz 의 tools/review-requests/Code.gs.
 *
 * - POST(본문 JSON, text/plain): { slug, title, page, name, text } → 탭 「의견」에 한 줄. 답 { ok, at }.
 * - GET ?action=list: 항목마다 의견 수·마지막 시각·처리 상태, 그리고 **팀이 공개로 표시한 의견만**.
 *     답 { ok, mode, items: { slug: { count, last, status, public: [ { at, name, text, status, reply } ] } } }
 *
 * ★ 공개 규칙은 스크립트 속성 PUBLISH가 정한다(코드를 고치거나 다시 배포하지 않고 바꾼다).
 *   - `바로`  : 받은 의견을 바로 내보낸다. 시트의 「공개」 칸에 `숨김`이라고 적은 줄만 뺀다.
 *   - 그 밖(비어 있음·`확인`): 「공개」 칸에 `공개`라고 적은 줄만 내보낸다. 나머지는 건수만 센다.
 *   로그인이 없어 누구나 아무 이름으로 쓸 수 있다 — `바로`일 때는 시트를 가끔 보고 `숨김`으로 내린다.
 * ★ 시트 ID는 코드에 두지 않는다(이 파일은 공개 저장소에 있다). 스크립트 속성 SHEET_ID에 넣는다.
 * ★ 익명 웹앱(실행: 나 / 액세스: 모든 사용자)이라 고급 Sheets 서비스(Sheets v4)를 쓴다.
 * ★ 쓰기는 LockService로 줄 세우고, 조회는 CacheService로 20초 묶는다(쓰면 지운다).
 * ★ 정적 페이지라 비밀값을 둘 수 없다 — 길이 제한·항목 ID 모양 검사·10분에 30건 상한으로 막는다.
 * ★ 값은 RAW로 넣는다 — 「=」로 시작하는 글이 수식이 되지 않게.
 */
var TAB = '의견';
var HEAD = ['보낸 시각', '항목 ID', '항목 제목', '보낸 사람', '의견', '페이지', '처리 상태', '공개', '팀의 답'];
var LIST_KEY = 'list-v2';
var LIMIT_PER_10MIN = 30;
var PUBLIC_WORD = '공개';
var HIDE_WORD = '숨김';
var PUBLIC_MAX_PER_ITEM = 50;
var PAGE_PREFIX = /^https:\/\/edufit-tech\.github\.io\/dfz-review\//;

function sheetId() {
  var id = PropertiesService.getScriptProperties().getProperty('SHEET_ID');
  if (!id) throw new Error('no-sheet-id');
  return id;
}

/** 받은 값을 검사해 시트 한 줄로. 틀리면 { ok:false, error }. 순수 함수(검사용). */
function buildRow(p, at) {
  if (!p || typeof p !== 'object') return { ok: false, error: 'bad-body' };
  var slug = String(p.slug || '').trim();
  var text = String(p.text || '').trim();
  var name = String(p.name || '').trim();
  var title = String(p.title || '').trim();
  var page = String(p.page || '').trim();
  if (!/^[a-z0-9][a-z0-9-]{1,59}$/.test(slug)) return { ok: false, error: 'bad-slug' };
  if (text.length < 2) return { ok: false, error: 'empty-text' };
  if (text.length > 1000) return { ok: false, error: 'too-long' };
  if (name.length > 40 || title.length > 120) return { ok: false, error: 'too-long' };
  if (page && !PAGE_PREFIX.test(page)) page = '';
  // 처리 상태·공개·팀의 답은 늘 빈칸으로 시작한다 — 보낸 사람이 채울 수 없다
  return { ok: true, row: [at, slug, title, name || '(이름 없음)', text, page, '', '', ''] };
}

/** 스크립트 속성 PUBLISH → 'now'(바로 공개) 또는 'review'(확인 뒤 공개). 모르는 값은 조심스러운 쪽. */
function publishMode() {
  var v = String(PropertiesService.getScriptProperties().getProperty('PUBLISH') || '').trim();
  return v === '바로' ? 'now' : 'review';
}

/** 「공개」 칸의 글과 방식 → 이 줄을 내보내는가. 순수 함수(검사용). */
function isShown(mark, mode) {
  mark = String(mark || '').trim();
  return mode === 'now' ? mark !== HIDE_WORD : mark === PUBLIC_WORD;
}

/** 시트 줄들 → 항목마다 요약. 순수 함수(검사용). 시각은 「yyyy-MM-dd HH:mm」 글이라 글자 비교가 시간 비교다. */
function summarize(rows, mode) {
  var items = {};
  for (var i = 0; i < rows.length; i++) {
    var r = rows[i] || [];
    var slug = String(r[1] || '');
    if (!slug) continue;
    var at = String(r[0] || '');
    var g = items[slug] || (items[slug] = { count: 0, last: '', status: '', public: [] });
    g.count++;
    if (at >= g.last) { g.last = at; g.status = String(r[6] || ''); }
    if (isShown(r[7], mode)) {
      g.public.push({
        at: at.slice(0, 10),                       // 날짜만 — 분 단위 시각은 내보내지 않는다
        name: String(r[3] || '').slice(0, 40),
        text: String(r[4] || '').slice(0, 1000),
        status: String(r[6] || '').slice(0, 40),
        reply: String(r[8] || '').slice(0, 1000)
      });
    }
  }
  for (var k in items) {
    var pub = items[k].public;
    pub.sort(function (a, b) { return a.at < b.at ? 1 : a.at > b.at ? -1 : 0; });   // 새 의견이 위
    if (pub.length > PUBLIC_MAX_PER_ITEM) pub.length = PUBLIC_MAX_PER_ITEM;
  }
  return items;
}

function doGet(e) {
  var action = e && e.parameter && e.parameter.action;
  if (action !== 'list') return json({ ok: false, error: 'unknown-action' });
  try {
    var mode = publishMode();
    var cached = cacheGet(LIST_KEY + mode);
    if (cached) return json(cached);
    var res = { ok: true, mode: mode, items: summarize(readRows(), mode) };
    cachePut(LIST_KEY + mode, res, 20);
    return json(res);
  } catch (err) {
    return json({ ok: false, error: 'read-failed' });
  }
}

function doPost(e) {
  var p;
  try { p = JSON.parse(e.postData.contents); } catch (err) { return json({ ok: false, error: 'bad-body' }); }
  var at = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm');
  var built = buildRow(p, at);
  if (!built.ok) return json(built);
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(15000);
  } catch (err) {
    return json({ ok: false, error: 'busy' });
  }
  try {
    if (!allowOne()) return json({ ok: false, error: 'rate-limit' });
    ensureTab();
    Sheets.Spreadsheets.Values.append({ values: [built.row] }, sheetId(), "'" + TAB + "'!A1",
      { valueInputOption: 'RAW', insertDataOption: 'INSERT_ROWS' });
    CacheService.getScriptCache().removeAll([LIST_KEY + 'now', LIST_KEY + 'review']);
    return json({ ok: true, at: at });
  } catch (err) {
    return json({ ok: false, error: 'write-failed' });
  } finally {
    lock.releaseLock();
  }
}

/** 탭이 없으면 만들고 머리줄을 쓴다. 있으면 6시간 기억해 다시 묻지 않는다. */
function ensureTab() {
  var cache = CacheService.getScriptCache();
  if (cache.get('tab-ok')) return;
  var id = sheetId();
  var meta = Sheets.Spreadsheets.get(id, { fields: 'sheets.properties.title' });
  var has = (meta.sheets || []).some(function (s) { return s.properties.title === TAB; });
  if (!has) {
    Sheets.Spreadsheets.batchUpdate({ requests: [{ addSheet: { properties: { title: TAB, gridProperties: { frozenRowCount: 1 } } } }] }, id);
    Sheets.Spreadsheets.Values.update({ values: [HEAD] }, id, "'" + TAB + "'!A1:I1", { valueInputOption: 'RAW' });
  }
  cache.put('tab-ok', '1', 21600);
}

function readRows() {
  try {
    var res = Sheets.Spreadsheets.Values.get(sheetId(), "'" + TAB + "'!A2:I");
    return res.values || [];
  } catch (err) {
    if (String(err).indexOf('Unable to parse range') >= 0) return [];   // 탭이 아직 없다 — 의견 0건
    throw err;
  }
}

/** 10분에 30건까지 — 넘으면 거절(익명 웹앱 도배 막기). */
function allowOne() {
  var cache = CacheService.getScriptCache();
  var key = 'rate-' + Math.floor(Date.now() / 600000);
  var n = Number(cache.get(key) || 0);
  if (n >= LIMIT_PER_10MIN) return false;
  cache.put(key, String(n + 1), 700);
  return true;
}

function cacheGet(k) { try { var v = CacheService.getScriptCache().get(k); return v ? JSON.parse(v) : null; } catch (e) { return null; } }
function cachePut(k, o, ttl) { try { var s = JSON.stringify(o); if (s.length < 95000) CacheService.getScriptCache().put(k, s, ttl); } catch (e) {} }
function json(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }

/** 처음 한 번 편집기에서 실행해 권한을 승인한다(익명 웹앱은 소유자 권한으로 돈다). 탭도 만든다. */
function authorize() {
  ensureTab();
  Logger.log('ok: ' + readRows().length + '줄');
}
