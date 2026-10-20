import os, sqlite3, secrets
from datetime import datetime, timezone, timedelta
from functools import wraps
from pathlib import Path
from flask import Flask, jsonify, request, session, send_from_directory, render_template_string, redirect, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('DATABASE_PATH', str(BASE_DIR / 'data' / 'events.sqlite3')))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
app = Flask(__name__, static_folder=None)
app.secret_key = os.environ.get('SESSION_SECRET') or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE','0') == '1', PERMANENT_SESSION_LIFETIME=timedelta(hours=8), MAX_CONTENT_LENGTH=16_384)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')
ALLOWED_EVENTS = {'session_started','first_envelope_opened','page_view','page_reading_time','answer','no_response_label_changed','music_play','music_pause','thank_you_music_play','thank_you_music_paused','thank_you_music_ended','thank_you_music_autoplay_blocked','countdown_started','final_letter_opened','thank_you_opened','session_exit'}
PAGES = {'1':'Memories','2':'Moving forward','3':'The question'}


def db():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.execute('''CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT NOT NULL,
            session_id TEXT NOT NULL,
            visitor_id TEXT NOT NULL DEFAULT '',
            duration_seconds INTEGER,
            page TEXT NOT NULL DEFAULT '',
            page_name TEXT NOT NULL DEFAULT '',
            question INTEGER,
            answer TEXT,
            attempt INTEGER,
            created_at TEXT NOT NULL
        )''')
        columns = {r['name'] for r in con.execute('PRAGMA table_info(events)').fetchall()}
        if 'visitor_id' not in columns:
            con.execute("ALTER TABLE events ADD COLUMN visitor_id TEXT NOT NULL DEFAULT ''")
        if 'duration_seconds' not in columns:
            con.execute("ALTER TABLE events ADD COLUMN duration_seconds INTEGER")
        con.execute('CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id)')
        con.execute('CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at DESC)')

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'ok': False, 'error':'login_required'}), 401
        return fn(*args, **kwargs)
    return wrapper

@app.after_request
def security_headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['Referrer-Policy'] = 'same-origin'
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['Cache-Control'] = 'no-store' if request.path.startswith('/api/admin') or request.path == '/admin' else 'no-cache'
    return resp

@app.get('/')
def home():
    return send_from_directory(BASE_DIR, 'index.html')

@app.get('/<path:filename>')
def static_files(filename):
    # Only serve the site's frontend files; never expose the database or Python files.
    if filename.startswith(('assets/', 'styles.css', 'script.js', 'favicon')):
        return send_from_directory(BASE_DIR, filename)
    return ('Not found', 404)

@app.post('/api/events')
def collect_event():
    data = request.get_json(silent=True) or {}
    event = str(data.get('event',''))[:40]
    if event not in ALLOWED_EVENTS:
        return jsonify({'ok':False,'error':'event_not_allowed'}), 400
    sid = str(data.get('session_id',''))[:100]
    if not sid or len(sid) < 8:
        return jsonify({'ok':False,'error':'invalid_session'}), 400
    visitor_id = str(data.get('visitor_id',''))[:100]
    if not visitor_id: visitor_id = sid
    duration_seconds = data.get('duration_seconds') if event in ('page_reading_time','session_exit') else None
    if event in ('page_reading_time','session_exit') and duration_seconds is not None and (not isinstance(duration_seconds, (int,float)) or duration_seconds < 0 or duration_seconds > 86400):
        return jsonify({'ok':False,'error':'invalid_duration'}), 400
    page = str(data.get('page',''))[:30]
    page_name = str(data.get('page_name',''))[:100]
    question = data.get('question')
    answer = data.get('answer')
    attempt = data.get('attempt')
    if event == 'answer':
        if question not in (1,2,3) or answer not in ('YES','NO') or not isinstance(attempt,int) or attempt < 1 or attempt > 10:
            return jsonify({'ok':False,'error':'invalid_answer'}), 400
    elif event == 'no_response_label_changed':
        if question not in (1,2,3) or not isinstance(attempt,int) or attempt < 1 or attempt > 3:
            return jsonify({'ok':False,'error':'invalid_no_attempt'}), 400
        answer = None
    else:
        question = None; answer = None; attempt = None
    stamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
    try:
        with db() as con:
            con.execute('INSERT INTO events(event,session_id,visitor_id,duration_seconds,page,page_name,question,answer,attempt,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                        (event,sid,visitor_id,duration_seconds,page,page_name,question,answer,attempt,stamp))
    except sqlite3.Error:
        app.logger.exception('Could not store analytics event')
        return jsonify({'ok':False,'error':'storage_error'}), 500
    return jsonify({'ok':True}), 201

LOGIN_PAGE = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>12.20_Mine — Private Admin</title><style>
*{box-sizing:border-box}body{margin:0;background:#0c0712;color:#fff;font-family:Arial,sans-serif;padding:24px}.wrap{max-width:900px;margin:auto}.card{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);border-radius:20px;padding:20px;margin:16px 0}h1{margin-bottom:6px}.muted{opacity:.7}input,button{font:inherit;border-radius:12px;padding:12px}input{width:min(100%,420px);display:block;margin:10px 0;background:#160d20;color:#fff;border:1px solid #5d416b}button{border:0;background:linear-gradient(135deg,#ff4fa3,#8b5cf6);color:#fff;font-weight:700;cursor:pointer}.err{color:#ff9fbf}.ok{color:#9fffbf}</style></head><body><div class="wrap"><h1>12.20_Mine ❤️</h1><div class="muted">Private interaction dashboard</div><div class="card"><h2>Admin access</h2><p class="muted">Enter your private admin credentials.</p><form method="post"><input name="username" placeholder="Username" autocomplete="username" required><input name="password" type="password" placeholder="Admin password" autocomplete="current-password" required><button type="submit">Open dashboard</button></form>{% if error %}<p class="err">{{ error }}</p>{% endif %}<p class="muted">This page is public, but the statistics are protected by server-side login.</p></div></div></body></html>'''

@app.route('/admin', methods=['GET','POST'])
def admin_page():
    if session.get('is_admin'):
        return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        if not ADMIN_PASSWORD:
            error = 'Admin is not configured yet. Set ADMIN_PASSWORD on the server.'
        elif secrets.compare_digest(request.form.get('username',''), ADMIN_USERNAME) and secrets.compare_digest(request.form.get('password',''), ADMIN_PASSWORD):
            session.clear(); session['is_admin'] = True; session.permanent = True
            return redirect(url_for('dashboard'))
        else:
            error = 'Incorrect username or password.'
    return render_template_string(LOGIN_PAGE, error=error)

DASHBOARD = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Private Analytics</title><style>
*{box-sizing:border-box}body{margin:0;background:#0c0712;color:#fff;font-family:Arial,sans-serif;padding:18px}.wrap{max-width:760px;margin:auto}.top{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.muted{color:#c7bdcf;font-size:14px;line-height:1.5}.card{background:#17101f;border:1px solid #49364f;border-radius:14px;padding:16px;margin:14px 0}.title{font-size:21px;font-weight:700;margin:0}.line{padding:7px 0;border-bottom:1px solid #302338;line-height:1.45}.line:last-child{border-bottom:0}.strong{font-weight:700}.actions{display:flex;gap:8px;flex-wrap:wrap}button{font:inherit;border:1px solid #75557d;border-radius:9px;padding:9px 12px;background:#291a32;color:#fff;cursor:pointer}.status{color:#f5c6e5}.good{color:#a7f3c0}.bad{color:#f9b3c4}.empty{padding:18px;border:1px dashed #75557d;border-radius:12px;color:#c7bdcf;margin-top:14px}form{margin:0}@media(max-width:480px){body{padding:12px}.card{padding:13px}.title{font-size:19px}}</style></head><body><main class="wrap"><div class="top"><div><h1 class="title">📊 Private Analytics</h1><p class="muted">Activity recorded as described on the opening screen. Times are approximate when a browser closes unexpectedly.</p><div id="updated" class="muted">Loading…</div></div><div class="actions"><button id="refresh" type="button">Refresh</button><button type="button" onclick="location.href='/api/admin/export.csv'">Export CSV</button><form method="post" action="/admin/logout"><button type="submit">Log out</button></form></div></div><div id="records"></div><script>
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function yesNo(v){return v?'<span class="good">Yes ✅</span>':'<span class="bad">No</span>'}
function stamp(v){if(!v)return '—';const d=new Date(v);return Number.isNaN(d.getTime())?v:d.toLocaleString()}
async function load(){const r=await fetch('/api/admin/stats',{credentials:'same-origin'});if(r.status===401){location.href='/admin';return}if(!r.ok)throw Error('load');const d=await r.json();const root=document.getElementById('records');root.replaceChildren();if(!d.sessions_detail.length){root.innerHTML='<div class="empty">No visitor activity recorded yet. Visit the public website to create a test record.</div>';}for(const v of d.sessions_detail){const card=document.createElement('section');card.className='card';card.innerHTML=`<div class="line strong">Visitor ${esc(v.visitor_number)} · Visit ${esc(v.visit_number)}</div><div class="line"><span class="strong">Started:</span> ${esc(stamp(v.started))}</div><div class="line"><span class="strong">Last Seen:</span> ${esc(stamp(v.last_seen))}</div><div class="line"><span class="strong">Time on website:</span> ${esc(v.total_seconds)} sec (estimated)</div><div class="line"><span class="strong">First envelope opened:</span> ${yesNo(v.envelope_opened)} · ${esc(stamp(v.envelope_time))}</div><div class="line"><span class="strong">Time until envelope:</span> ${esc(v.time_until_envelope_seconds===null?'—':v.time_until_envelope_seconds+' sec')}</div><div class="line"><span class="strong">Current Screen:</span> ${esc(v.current_screen||'unknown')}</div><div class="line">Reached Page 2: ${yesNo(v.reached_page_2)}</div><div class="line">Reached Page 3: ${yesNo(v.reached_page_3)}</div><div class="line">Reached Reveal: ${yesNo(v.reached_reveal)}</div><div class="line">Reached Envelope: ${yesNo(v.reached_envelope)} 💌</div><div class="line">Opened Letter: ${yesNo(v.opened_letter)} ❤️✨</div><div class="line">Thank-you Note: ${yesNo(v.thank_you_opened)}</div><div class="line"><span class="strong">YES Progress:</span> P1: ${esc(v.yes_progress[0])}, P2: ${esc(v.yes_progress[1])}, P3: ${esc(v.yes_progress[2])}</div><div class="line"><span class="strong">NO Button Attempts:</span> P1: ${esc(v.no_attempts[0])}, P2: ${esc(v.no_attempts[1])}, P3: ${esc(v.no_attempts[2])}</div><div class="line"><span class="strong">Reading Time:</span> P1: ${esc(v.reading_seconds[0])}s, P2: ${esc(v.reading_seconds[1])}s, P3: ${esc(v.reading_seconds[2])}s, Thank-you: ${esc(v.thank_you_seconds)}s</div><details style="margin-top:12px"><summary style="cursor:pointer;color:#f5c6e5">Activity timeline</summary><div style="margin-top:8px">${v.timeline.map(e=>`<div class="line">${esc(stamp(e.created_at))} · ${esc(e.event)}${e.question?` · Q${esc(e.question)}`:''}${e.answer?` · ${esc(e.answer)}`:''}${e.duration_seconds!==null&&e.duration_seconds!==undefined?` · ${esc(e.duration_seconds)}s`:''}</div>`).join('')}</div></details>`;root.appendChild(card)}document.getElementById('updated').textContent='Updated: '+new Date().toLocaleString()}
document.getElementById('refresh').addEventListener('click',()=>load().catch(()=>alert('Could not load private analytics.')));load().catch(()=>{document.getElementById('records').innerHTML='<div class="empty">Could not load private analytics. Please sign in again.</div>'});
</script></main></body></html>'''

@app.get('/admin/dashboard')
@admin_required
def dashboard():
    return DASHBOARD

@app.post('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('admin_page'))

@app.get('/api/admin/stats')
@admin_required
def admin_stats():
    with db() as con:
        rows = con.execute('SELECT * FROM events ORDER BY created_at ASC, id ASC').fetchall()
    events = [dict(r) for r in rows]
    grouped = {}
    visitor_first_seen = {}
    for e in events:
        sid = e['session_id']
        grouped.setdefault(sid, []).append(e)
        vid = e.get('visitor_id') or sid
        if vid not in visitor_first_seen:
            visitor_first_seen[vid] = e['created_at']
    visitor_order = {vid: i + 1 for i, (vid, _) in enumerate(sorted(visitor_first_seen.items(), key=lambda kv: kv[1]))}
    session_details = []
    # Each session is one visit record. Repeat sessions with the same anonymous browser ID
    # share a visitor number, while each visit gets its own visit number.
    chronological_sessions = sorted(grouped.items(), key=lambda kv: kv[1][0]['created_at'])
    visit_numbers = {}
    session_visit_number = {}
    for sid, evs in chronological_sessions:
        vid = next((e.get('visitor_id') for e in evs if e.get('visitor_id')), sid)
        visit_numbers[vid] = visit_numbers.get(vid, 0) + 1
        session_visit_number[sid] = visit_numbers[vid]
    ordered_sessions = list(reversed(chronological_sessions))
    for sid, evs in ordered_sessions:
        vid = next((e.get('visitor_id') for e in evs if e.get('visitor_id')), sid)
        page_views = [e for e in evs if e['event'] == 'page_view']
        current_screen = page_views[-1]['page'] if page_views else (evs[-1].get('page') or 'unknown')
        reached = {e.get('page') for e in page_views}
        answers = {1: [], 2: [], 3: []}
        reading_seconds = {1: 0, 2: 0, 3: 0}
        for e in evs:
            if e['event'] == 'answer' and e.get('question') in answers:
                answers[e['question']].append(e.get('answer'))
            if e['event'] == 'page_reading_time' and e.get('duration_seconds') is not None:
                page = e.get('page')
                q = {'p1': 1, 'p2': 2, 'p3': 3}.get(page)
                if q:
                    reading_seconds[q] += int(e['duration_seconds'])
        started = next((e['created_at'] for e in evs if e['event'] == 'session_started'), evs[0]['created_at'])
        last_seen = evs[-1]['created_at']
        envelope_event = next((e for e in evs if e['event'] == 'first_envelope_opened'), None)
        exit_event = next((e for e in reversed(evs) if e['event'] == 'session_exit' and e.get('duration_seconds') is not None), None)
        try:
            total_seconds = int(exit_event['duration_seconds']) if exit_event else max(0, int((datetime.fromisoformat(last_seen.replace('Z','+00:00')) - datetime.fromisoformat(started.replace('Z','+00:00'))).total_seconds()))
            time_until_envelope = max(0, int((datetime.fromisoformat(envelope_event['created_at'].replace('Z','+00:00')) - datetime.fromisoformat(started.replace('Z','+00:00'))).total_seconds())) if envelope_event else None
        except Exception:
            total_seconds = 0; time_until_envelope = None
        thank_you_seconds = sum(int(e['duration_seconds']) for e in evs if e['event'] == 'page_reading_time' and e.get('page') in ('thanks','thank-you'))
        session_details.append({
            'visitor_number': visitor_order.get(vid, 1),
            'visit_number': session_visit_number[sid],
            'started': started,
            'last_seen': last_seen,
            'total_seconds': total_seconds,
            'envelope_opened': envelope_event is not None,
            'envelope_time': envelope_event['created_at'] if envelope_event else None,
            'time_until_envelope_seconds': time_until_envelope,
            'thank_you_seconds': thank_you_seconds,
            'timeline': [{k:e.get(k) for k in ('event','created_at','page','question','answer','attempt','duration_seconds')} for e in evs],
            'current_screen': current_screen,
            'reached_page_2': 'p2' in reached,
            'reached_page_3': 'p3' in reached,
            'reached_reveal': 'reveal' in reached or 'countdown' in reached,
            'reached_envelope': any(e['event'] == 'first_envelope_opened' for e in evs),
            'opened_letter': any(e['event'] == 'final_letter_opened' for e in evs),
            'thank_you_opened': any(e['event'] == 'thank_you_opened' for e in evs) or 'thanks' in reached,
            'yes_progress': ['YES' if 'YES' in answers[q] else '—' for q in (1, 2, 3)],
            'no_attempts': [sum(1 for a in answers[q] if a == 'NO') for q in (1, 2, 3)],
            'reading_seconds': [reading_seconds[q] for q in (1, 2, 3)],
        })
    # Basic counts remain available for compatibility with any older admin views.
    sessions = len(grouped)
    visitors = len(visitor_first_seen)
    pages = {}
    for p in (1, 2, 3):
        qrows = [e for e in events if e['event'] == 'answer' and e.get('question') == p]
        pages[str(p)] = {
            'yes': sum(1 for e in qrows if e.get('answer') == 'YES'),
            'no': sum(1 for e in qrows if e.get('answer') == 'NO'),
            'views': sum(1 for e in events if e['event'] == 'page_view' and e.get('page') == f'p{p}'),
            'final_yes': sum(1 for e in qrows if e.get('answer') == 'YES') if p == 3 else 0,
        }
    reading = [e['duration_seconds'] for e in events if e['event'] == 'page_reading_time' and e.get('duration_seconds') is not None]
    recent = [{k: e.get(k) for k in ('event','session_id','page','page_name','question','answer','attempt','duration_seconds','created_at')} for e in reversed(events[-100:])]
    return jsonify({'ok': True, 'sessions': sessions, 'total_yes': sum(x['yes'] for x in pages.values()), 'total_no': sum(x['no'] for x in pages.values()), 'pages': pages, 'visitors': visitors, 'reading_events': len(reading), 'average_reading_seconds': round(sum(reading) / len(reading), 1) if reading else 0, 'music_plays': sum(1 for e in events if e['event'] in ('music_play','thank_you_music_play')), 'thank_you': sum(1 for e in events if e['event'] == 'thank_you_opened'), 'recent': recent, 'sessions_detail': session_details})


@app.get('/api/admin/export.csv')
@admin_required
def export_csv():
    import csv, io
    with db() as con:
        rows = con.execute('SELECT event,session_id,visitor_id,page,page_name,question,answer,attempt,duration_seconds,created_at FROM events ORDER BY created_at ASC,id ASC').fetchall()
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(['event','session_id','anonymous_visitor_id','page','page_name','question','answer','attempt','duration_seconds','timestamp_utc'])
    for row in rows: writer.writerow(list(row))
    from flask import Response
    return Response(stream.getvalue(), mimetype='text/csv', headers={'Content-Disposition':'attachment; filename="anniversary-analytics.csv"'})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT','5000')), debug=False)
else:
    init_db()
