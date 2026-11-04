# Generates the terminal-style animated SVGs in images/. Run from the repo root: python scripts/art.py
# Font (JetBrains Mono, OFL) is embedded as base64 so it renders inside GitHub's <img> sandbox.
import base64, json, os, random, re, subprocess, sys, urllib.request

random.seed(5)
W = 900
BG, BAR, LINE = '#0a0e14', '#0f1520', '#1f2937'
ACCENT = '#38bdf8'
TXT, DIM, GREEN, CYAN, INDIGO, KEY, STR = '#c9d1d9', '#6b7280', ACCENT, ACCENT, '#9ca3af', '#9ca3af', '#e6edf3'


def b64(path):
    return base64.b64encode(open(path, 'rb').read()).decode()


FONT_CSS = ''.join(
    f"@font-face{{font-family:'JB';font-weight:{w};src:url(data:font/woff2;base64,{b64(f'fonts/jb-{w}.woff2')}) format('woff2')}}"
    for w in (400, 700))
FF = "font-family=\"JB,monospace\""

DEFS = f'''<defs>
<linearGradient id="ng" x1="0" x2="1"><stop offset="0" stop-color="#f1f5f9"/><stop offset="1" stop-color="#7dd3fc"/></linearGradient>
<linearGradient id="bd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#38bdf8"/><stop offset="1" stop-color="#38bdf8"/></linearGradient>
<radialGradient id="gl"><stop offset="0" stop-color="#38bdf8" stop-opacity=".16"/><stop offset="1" stop-color="#6366f1" stop-opacity="0"/></radialGradient>
<filter id="mono"><feColorMatrix type="saturate" values="0"/></filter>

</defs>'''

BASE_CSS = FONT_CSS + '''
text{font-family:'JB',monospace}
.ln{opacity:0;animation:in .25s ease-out forwards}@keyframes in{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:none}}
.ty{transform-box:fill-box;transform-origin:left;transform:scaleX(0);animation:ty var(--d) steps(var(--n)) forwards}@keyframes ty{to{transform:scaleX(1)}}
.cur{animation:bl 1s steps(1) infinite}@keyframes bl{50%{opacity:0}}
.cell{opacity:0;animation:fade .4s ease-out forwards}@keyframes fade{to{opacity:1}}
.today{animation:today 1.8s ease-in-out infinite}@keyframes today{50%{opacity:.25}}
.tick{animation:tick 1.4s cubic-bezier(.2,.8,.2,1) forwards}@keyframes tick{from{transform:translateY(0)}to{transform:translateY(var(--to))}}
.ring{stroke-dashoffset:var(--c);animation:ring 1.4s cubic-bezier(.2,.8,.2,1) forwards}@keyframes ring{to{stroke-dashoffset:var(--e)}}
.beam{stroke-dasharray:14 86;animation:beam 6s linear infinite}@keyframes beam{to{stroke-dashoffset:-100}}
.pop{opacity:0;transform:scale(.2);animation:pop 1s cubic-bezier(.2,.8,.2,1) forwards}@keyframes pop{to{opacity:1;transform:scale(1)}}
.grow{transform-box:fill-box;transform-origin:left;transform:scaleX(0);animation:gx 1.2s cubic-bezier(.2,.8,.2,1) forwards}@keyframes gx{to{transform:scaleX(1)}}
.up{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:gy 1s cubic-bezier(.2,.8,.2,1) forwards}@keyframes gy{to{transform:scaleY(1)}}

'''

_cid = [0]
FAST = '.ln,.ty,.cell,.grow,.up,.pop,.tick,.ring{animation-delay:-60s!important}.beam,.lit{animation:none!important}.pk{animation:none!important;opacity:0}.nn,.q,.wv{animation-delay:-1.2s!important;animation-play-state:paused!important}text[style*="animation:f"]{animation:none!important;opacity:1!important}' if os.environ.get('FAST') else ''  # preview only: show final frame


def svg(h, label, css, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}" role="img" aria-label="{label}">'
            f'<style>{BASE_CSS}{css}{FAST}</style>{DEFS}{body}</svg>\n')


def window(h, title):
    return (f'<rect x=".5" y=".5" width="{W-1}" height="{h-1}" rx="12" fill="{BG}" stroke="{LINE}"/>'
            f'<path d="M1 34V13a12 12 0 0 1 12-12h{W-26}a12 12 0 0 1 12 12v21z" fill="{BAR}"/>'
            f'<circle cx="24" cy="18" r="6" fill="#2b3340"/><circle cx="46" cy="18" r="6" fill="#2b3340"/><circle cx="68" cy="18" r="6" fill="#2b3340"/>'
            f'<text x="{W//2}" y="22" text-anchor="middle" font-size="12" fill="{DIM}">{title}</text>'
            f'<rect x="1" y="34" width="{W-2}" height="1" fill="{LINE}"/>')


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def typed(x, y, parts, delay, size=14):
    """Types a line of [(text, color), ...] left to right. Returns (svg, end_time)."""
    _cid[0] += 1
    if _cid[0] > 1:  # only the first command types out; the rest just appear
        return line(x, y, parts, delay, size), delay + 0.2
    n = sum(len(t) for t, _ in parts)
    cw = size * 0.6
    dur = n * 0.045
    cid = f'c{_cid[0]}'
    tspans = ''.join(f'<tspan fill="{c}">{esc(t)}</tspan>' for t, c in parts)
    s = (f'<clipPath id="{cid}"><rect x="{x}" y="{y-size-2}" width="{n*cw+4}" height="{size+10}" class="ty" '
         f'style="--d:{dur:.2f}s;--n:{n};animation-delay:{delay:.2f}s"/></clipPath>'
         f'<text x="{x}" y="{y}" font-size="{size}" clip-path="url(#{cid})" xml:space="preserve">{tspans}</text>')
    return s, delay + dur


def line(x, y, parts, delay, size=14):
    tspans = ''.join(f'<tspan fill="{c}">{esc(t)}</tspan>' for t, c in parts)
    return f'<text x="{x}" y="{y}" font-size="{size}" class="ln" style="animation-delay:{delay:.2f}s" xml:space="preserve">{tspans}</text>'


def caret(x, y, delay, size=14):
    return f'<rect x="{x}" y="{y-size}" width="{size*0.55:.1f}" height="{size+3}" fill="{GREEN}" class="ln" style="animation-delay:{delay:.2f}s"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1s" begin="{delay:.2f}s" repeatCount="indefinite"/></rect>'


OUT = sys.argv[1] if len(sys.argv) > 1 else 'out'


def save(name, s):
    os.makedirs(OUT, exist_ok=True)
    open(f'{OUT}/{name}', 'w', encoding='utf-8').write(s)




# ------------------------------------------------------------------ live GitHub analytics (needs a token: GH_TOKEN env or `gh auth token`)
USER = os.environ.get('GH_USER', 'oahednoorforhad')
GQL = '''query($login:String!){user(login:$login){

 contributionsCollection{restrictedContributionsCount totalCommitContributions totalPullRequestContributions
  totalIssueContributions totalPullRequestReviewContributions
  contributionCalendar{totalContributions weeks{contributionDays{date contributionCount contributionLevel weekday}}}}
 repositories(first:100, ownerAffiliations:[OWNER,ORGANIZATION_MEMBER,COLLABORATOR], isFork:false){
  nodes{languages(first:8, orderBy:{field:SIZE, direction:DESC}){edges{size node{name}}}}}}}'''


def fetch_stats():
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token:
        try:
            token = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True).stdout.strip()
        except Exception:
            token = ''
    if not token:
        return None
    req = urllib.request.Request('https://api.github.com/graphql',
                                 data=json.dumps({'query': GQL, 'variables': {'login': USER}}).encode(),
                                 headers={'Authorization': f'bearer {token}', 'User-Agent': 'profile-art'})
    for attempt in range(3):  # the GraphQL API fails transiently now and then; without this the stats section silently disappears
        try:
            return json.load(urllib.request.urlopen(req, timeout=30))['data']['user']
        except Exception as e:
            print('analytics attempt', attempt + 1, 'failed:', e)
    return None


def gh_token():
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token:
        try:
            token = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True).stdout.strip()
        except Exception:
            token = ''
    return token


def fetch_events(limit=6):
    """Latest activity grouped per day, kind and repo as (when, kind, repo, detail). Private repos are masked: no name, no message."""
    token = gh_token()
    if not token:
        return []
    events = []
    for page in (1, 2):
        req = urllib.request.Request(f'https://api.github.com/users/{USER}/events?per_page=100&page={page}',
                                     headers={'Authorization': f'bearer {token}', 'User-Agent': 'profile-art'})
        try:
            events += json.load(urllib.request.urlopen(req, timeout=30))
        except Exception as e:
            print('events skipped:', e)
            break
    groups = {}
    for e in events:
        pub = e.get('public', True)
        repo = e['repo']['name'].split('/')[-1] if pub else 'private repo'
        pl = e.get('payload', {})
        t = e['type']
        day = e['created_at'][:10]
        if t == 'PushEvent':
            n = pl.get('distinct_size') or len(pl.get('commits', []))
            if not n:
                continue
            kind = 'push'
            msg = pl['commits'][-1]['message'].split('\n')[0] if pub and pl.get('commits') else ''
            val = {'n': n, 'msg': msg}
        elif t == 'PullRequestEvent':
            pr = pl.get('pull_request', {})
            kind = 'pr'
            val = {'action': 'merged' if pr.get('merged') else pl.get('action', 'updated'), 'n': 1}
        elif t == 'CreateEvent' and pl.get('ref_type') == 'branch':
            kind, val = 'branch', {'n': 1}
        else:
            continue
        g = groups.setdefault((day, kind, repo), {'when': e['created_at'], 'n': 0, 'actions': {}, 'msg': ''})
        g['n'] += val['n']
        if 'action' in val:
            g['actions'][val['action']] = g['actions'].get(val['action'], 0) + 1
        if val.get('msg') and not g['msg']:
            g['msg'] = val['msg']  # events arrive newest first, so this is the latest message
    out = []
    for (day, kind, repo), g in sorted(groups.items(), key=lambda kv: kv[1]['when'], reverse=True)[:limit]:
        d = g['when']
        when = f"{mn_names[int(d[5:7]) - 1]} {d[8:10]} {d[11:16]}"
        if kind == 'push':
            detail = f"{g['n']} commit{'s' if g['n'] != 1 else ''}" + (f": {g['msg'][:38]}" if g['msg'] else '')
        elif kind == 'pr':
            detail = ', '.join(f'{c} {a}' for a, c in g['actions'].items())
        else:
            detail = f"{g['n']} new branch{'es' if g['n'] != 1 else ''}"
        out.append((when, kind, repo, detail))
    return out


mn_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def activity_feed(y, t, rows):
    """Looping log: lines appear one after another, hold, fade, repeat. Real data, so the loop means something."""
    cycle = 14
    css_ = ''
    out = ''
    for i, (d, kind, repo, detail) in enumerate(rows):
        a = 3 + i * 8  # percent of the cycle at which this line shows up
        css_ += (f'@keyframes f{i}{{0%,{a}%{{opacity:0;transform:translateY(-12px)}}{a + 2}%{{opacity:1;transform:translateY(2px)}}{a + 4}%,86%{{opacity:1;transform:none}}93%,100%{{opacity:0}}}}')
        out += (f'<text x="32" y="{y + i*22}" font-size="12" opacity="0" style="animation:f{i} {cycle}s ease-out infinite;animation-delay:{t:.2f}s" xml:space="preserve">'
                f'<tspan fill="{DIM}">{d}  </tspan><tspan fill="{ACCENT}">{kind:<8}</tspan><tspan fill="{STR}">{esc(repo):<22}</tspan><tspan fill="{KEY}">{esc(detail)}</tspan></text>')
    return out, css_, y + len(rows) * 22, t + 0.5


RAMP = ['#141a24', '#12384f', '#16597d', '#2589b8', '#38bdf8']


_tid = [0]


def ticker(x, y, text, size, delay, fill=None):
    """Number Ticker: every digit is a 0-9 strip that rolls to its value; other characters stay put."""
    fill = fill or STR
    cw, lh = size * 0.6, size * 1.25
    out = ''
    for i, ch in enumerate(text):
        cx = x + i * cw
        if not ch.isdigit():
            out += f'<text x="{cx:.1f}" y="{y}" font-size="{size}" font-weight="700" fill="{fill}">{esc(ch)}</text>'
            continue
        _tid[0] += 1
        cid = f't{_tid[0]}'
        strip = ''.join(f'<text x="{cx:.1f}" y="{y + k * lh:.1f}" font-size="{size}" font-weight="700" fill="{fill}">{k}</text>' for k in range(10))
        out += (f'<clipPath id="{cid}"><rect x="{cx:.1f}" y="{y - size * 0.82:.1f}" width="{cw + 1:.1f}" height="{lh:.1f}"/></clipPath>'
                f'<g clip-path="url(#{cid})"><g class="tick" style="--to:{-int(ch) * lh:.1f}px;animation-delay:{delay + i * 0.09:.2f}s">{strip}</g></g>')
    return out


def panel_title(x, y, text):
    return f'<text x="{x}" y="{y}" font-size="11" fill="{DIM}"># {text}</text>'


def analytics(y, t, u):
    """Clean layout: 4 stat tiles, heatmap with month labels, monthly bars + top languages, one insights row."""
    cc = u['contributionsCollection']
    cal = cc['contributionCalendar']
    weeks = cal['weeks']
    days = [d for w in weeks for d in w['contributionDays']]
    total = cal['totalContributions']
    priv = cc['restrictedContributionsCount']
    best = run = 0
    for d in days:
        run = run + 1 if d['contributionCount'] else 0
        best = max(best, run)
    cur = 0
    for d in reversed(days):
        if d['contributionCount']:
            cur += 1
        elif d is not days[-1]:
            break
    active = sum(1 for d in days if d['contributionCount'])
    out = ''

    # --- 4 stat tiles
    tiles = [(f'{total:,}', 'contributions', f'{priv:,} private . {total - priv:,} public'),
             (f'{cur}', 'current streak', 'days in a row'),
             (f'{best}', 'longest streak', 'days in a row'),
             (f'{100*active/len(days):.0f}%', 'active days', f'{active} of {len(days)} days')]
    gapx = 12
    bw = (W - 64 - 3 * gapx) / 4
    for i, (v, label, sub) in enumerate(tiles):
        x = 32 + i * (bw + gapx)
        d0 = t + i * 0.1
        ring = ''
        if v.endswith('%'):
            cx_, cy_, circ = x + bw - 34, y + 37, 2 * 3.14159 * 16
            pct = float(v[:-1])
            ring = (f'<circle cx="{cx_:.1f}" cy="{cy_}" r="16" fill="none" stroke="#141a24" stroke-width="4"/>'
                    f'<circle class="ring" cx="{cx_:.1f}" cy="{cy_}" r="16" fill="none" stroke="{ACCENT}" stroke-width="4" stroke-linecap="round" '
                    f'stroke-dasharray="{circ:.1f}" transform="rotate(-90 {cx_:.1f} {cy_})" style="--c:{circ:.1f};--e:{circ * (1 - pct / 100):.1f};animation-delay:{d0 + 0.3:.2f}s"/>')
        out += (f'<g class="ln" style="animation-delay:{d0:.2f}s"><rect x="{x:.1f}" y="{y}" width="{bw:.1f}" height="80" rx="10" fill="#0f1520" stroke="{LINE}"/>'
                + ticker(x + 16, y + 34, v, 26, d0 + 0.2) +
                f'<text x="{x+16:.1f}" y="{y+52}" font-size="11" fill="{ACCENT}">{label}</text>'
                f'<text x="{x+16:.1f}" y="{y+68}" font-size="11" fill="{DIM}">{sub}</text>' + ring +
                (f'<rect class="beam" x="{x:.1f}" y="{y}" width="{bw:.1f}" height="80" rx="10" fill="none" stroke="{ACCENT}" stroke-width="1.5" pathLength="100"/>' if label == 'current streak' else '') + '</g>')
    y += 112

    # --- heatmap with month labels
    lvl = {'NONE': 0, 'FIRST_QUARTILE': 1, 'SECOND_QUARTILE': 2, 'THIRD_QUARTILE': 3, 'FOURTH_QUARTILE': 4}
    mn = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    cs, gap = 12, 3
    x0 = 32
    sx = (W - 64 - cs) / (len(weeks) - 1)  # column step so the last week ends at the right edge
    last_m = None
    labels = ''
    for wi, w in enumerate(weeks):
        m = w['contributionDays'][0]['date'][5:7]
        if m != last_m and wi < len(weeks) - 2:
            labels += f'<text x="{x0 + wi*sx:.1f}" y="{y}" font-size="11" fill="{DIM}">{mn[int(m) - 1]}</text>'
        last_m = m
    out += labels
    y += 12
    for wi, w in enumerate(weeks):
        cells = ''.join(f'<rect x="{x0 + wi*sx:.1f}" y="{y + di*(cs+gap)}" width="{cs}" height="{cs}" rx="3" fill="{RAMP[lvl.get(d["contributionLevel"], 0)]}"/>'
                        for di, d in enumerate(w['contributionDays']))
        out += f'<g class="cell" style="animation-delay:{t + wi*0.03:.2f}s">{cells}</g>'
    lw = weeks[-1]['contributionDays']
    tx, ty = x0 + (len(weeks) - 1) * sx, y + (len(lw) - 1) * (cs + gap)
    out += (f'<rect class="today" x="{tx - 1.5:.1f}" y="{ty - 1.5}" width="{cs + 3}" height="{cs + 3}" rx="4" fill="none" stroke="{STR}" stroke-width="1.5"/>'
            f'<text x="{tx + cs:.1f}" y="{y + 7 * (cs + gap) + 12}" text-anchor="end" font-size="11" fill="{DIM}">today</text>')
    y += 7 * (cs + gap) + 34
    t += 0.4 + len(weeks) * 0.03

    # --- left: monthly bars (only the peak is labelled)
    by = {}
    for d in days:
        by[d['date'][:7]] = by.get(d['date'][:7], 0) + d['contributionCount']
    months = sorted(by)[-12:]
    mx = max(by[m] for m in months) or 1
    out += panel_title(32, y, 'contributions per month')
    base = y + 124
    for i, m in enumerate(months):
        h = max(3, 84 * by[m] / mx)
        x = 32 + i * 33
        peak = by[m] == mx
        out += (f'<rect x="{x}" y="{base - 16 - h:.1f}" width="24" height="{h:.1f}" rx="4" fill="{ACCENT}" fill-opacity="{1 if peak else 0.4}" class="up" style="animation-delay:{t + i*0.06:.2f}s"/>'
                f'<text x="{x+12}" y="{base - 2}" text-anchor="middle" font-size="11" fill="{DIM}">{mn[int(m[5:]) - 1]}</text>')
        if peak:
            out += f'<text x="{x+12}" y="{base - 22 - h:.1f}" text-anchor="middle" font-size="10" fill="{STR}">{by[m]}</text>'

    # --- right: top languages
    langs = {}
    for r_ in u['repositories']['nodes']:
        for e in r_['languages']['edges']:
            n = e['node']['name']
            if n != 'Jupyter Notebook':
                langs[n] = langs.get(n, 0) + e['size']
    ltot = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
    out += panel_title(470, y, 'top languages')
    for i, (n, sz) in enumerate(top):
        ly = y + 16 + i * 24
        pct = 100 * sz / ltot
        out += (f'<text x="470" y="{ly+11}" font-size="12" fill="{TXT}">{esc(n)}</text>'
                f'<rect x="590" y="{ly+1}" width="220" height="10" rx="5" fill="#141a24"/>'
                f'<rect x="590" y="{ly+1}" width="{max(220*pct/100, 3):.1f}" height="10" rx="5" fill="{ACCENT}" fill-opacity="{1 - i*0.15:.2f}" class="grow" style="animation-delay:{t + i*0.12:.2f}s"/>'
                f'<text x="868" y="{ly+11}" text-anchor="end" font-size="11" fill="{KEY}">{pct:.0f}%</text>')
    y += 160
    t += 1.2

    # --- one insights row
    best_day = max(days, key=lambda d: d['contributionCount'])
    wd = [0] * 7
    wn = [0] * 7
    for d in days:
        wd[d['weekday']] += d['contributionCount']
        wn[d['weekday']] += 1
    fav = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][max(range(7), key=lambda i: wd[i] / (wn[i] or 1))]
    items = [('busiest_day', f'{best_day["contributionCount"]} on {best_day["date"]}'),
             ('top_weekday', fav),
             ('avg_per_active_day', f'{total/(active or 1):.1f}')]
    for i, (k, v) in enumerate(items):
        ln_ = line((32, 470, W - 32)[i], y, [(k + ' ', KEY), ('= ', DIM), (v, STR)], t + i * 0.15, 12)
        out += ln_.replace('<text ', '<text text-anchor="end" ', 1) if i == 2 else ln_  # left panel, right panel, right edge
    y += 4
    t += 0.8
    return out, y, t


# ------------------------------------------------------------------ one terminal window
b = ''
y = 72
t = 0.3
css = ''
b += '<ellipse cx="260" cy="150" rx="330" ry="130" fill="url(#gl)"/>'

# hero: who, role, one sentence, focus tags
s, t = typed(32, y, [('$ ', GREEN), ('whoami', TXT)], t)
b += s
b += f'<text x="32" y="{y+66}" font-size="44" font-weight="700" fill="url(#ng)" class="ln" style="animation-delay:{t+0.2:.2f}s">Oahed Noor Forhad</text>'
t += 0.5
b += line(32, y + 100, [('AI Engineer', CYAN), ('  \u00b7  ', DIM), ('IEEE Published Researcher', STR), ('  \u00b7  ', DIM), ('Building AI Systems', STR)], t, 16)
b += line(32, y + 130, [('I enjoy building intelligent applications with LLMs, RAG and AI Agents.', KEY)], t + 0.15, 14)
x = 32
for i, tag in enumerate(['LLMs', 'RAG', 'AI Agents', 'Real-time voice agents']):
    voice = 'voice' in tag
    tw = len(tag) * 7.2
    w = tw + 24 + (26 if voice else 0)
    b += (f'<g class="ln" style="animation-delay:{t + 0.3 + i * 0.08:.2f}s"><rect x="{x:.1f}" y="{y+148}" width="{w:.1f}" height="26" rx="13" fill="#0f1a26" stroke="{ACCENT}" stroke-opacity=".45"/>'
          f'<text x="{x + 12:.1f}" y="{y+165}" font-size="12" fill="{STR}">{tag}</text>')
    if voice:  # live waveform: the agent is listening
        for k, dur in enumerate((.9, .6, 1.1, .7, .8)):
            b += f'<rect class="wv" x="{x + tw + 20 + k * 4:.1f}" y="{y+155}" width="2" height="12" rx="1" fill="{ACCENT}" style="animation-duration:{dur}s;animation-delay:{-k * .23:.2f}s"/>'
    b += '</g>'
    x += w + 8
css += '.wv{transform-box:fill-box;transform-origin:center;animation:wv .8s ease-in-out infinite alternate}@keyframes wv{from{transform:scaleY(.25)}to{transform:scaleY(1)}}'

# vector search: a query moves through embedding space and its 3 nearest neighbours light up
fx0, fy0, fw, fh = 704, 82, 152, 150  # panel = 692..868 x 56..246
pts = []
for cx_, cy_ in ((.25, .3), (.72, .25), (.5, .72), (.2, .8)):
    for _ in range(9):
        pts.append((fx0 + fw * min(max(random.gauss(cx_, .09), .04), .96), fy0 + fh * min(max(random.gauss(cy_, .09), .04), .96)))
qs = [(fx0 + fw * a, fy0 + fh * c) for a, c in ((.3, .36), (.66, .3), (.48, .66), (.24, .74))]
b += (f'<g class="ln" style="animation-delay:{t:.2f}s"><rect x="{fx0 - 12}" y="56" width="{fw + 24}" height="190" rx="12" fill="#0b111a" stroke="{LINE}" stroke-dasharray="3 4"/>'
      + ''.join(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.2" fill="#3b4656"/>' for px, py in pts)
      + f'<text x="{fx0}" y="74" font-size="11" fill="{DIM}"># vector search . top-3</text></g>')
CYQ = 12
kf = ''.join(f'{25 * k}%,{25 * k + 19}%{{transform:translate({qx - qs[0][0]:.1f}px,{qy - qs[0][1]:.1f}px)}}' for k, (qx, qy) in enumerate(qs))
css += f'.q{{animation:q {CYQ}s ease-in-out infinite}}@keyframes q{{{kf}100%{{transform:translate(0,0)}}}}.nn{{opacity:0;animation:nn0 {CYQ}s linear infinite}}'
for k, (qx, qy) in enumerate(qs):
    a, z = 25 * k + 2, 25 * k + 17
    css += f'@keyframes nn{k}{{0%,{a}%{{opacity:0;stroke-dashoffset:1}}{a + 3}%,{z}%{{opacity:1;stroke-dashoffset:0}}{z + 2}%,100%{{opacity:0}}}}'
    near = sorted(pts, key=lambda pp: (pp[0] - qx) ** 2 + (pp[1] - qy) ** 2)[:3]
    for px, py in near:
        st = f'animation-name:nn{k};animation-delay:{t + 0.4:.2f}s'
        b += (f'<line class="nn" x1="{qx:.1f}" y1="{qy:.1f}" x2="{px:.1f}" y2="{py:.1f}" stroke="{ACCENT}" stroke-opacity=".6" pathLength="1" stroke-dasharray="1" style="{st}"/>'
              f'<circle class="nn" cx="{px:.1f}" cy="{py:.1f}" r="3.6" fill="{ACCENT}" style="{st}"/>')
b += (f'<g class="q" style="animation-delay:{t + 0.4:.2f}s"><circle cx="{qs[0][0]:.1f}" cy="{qs[0][1]:.1f}" r="7" fill="{ACCENT}" fill-opacity=".15" stroke="{ACCENT}"/>'
      f'<circle cx="{qs[0][0]:.1f}" cy="{qs[0][1]:.1f}" r="2.5" fill="{STR}"/></g>')
t += 0.8

# now
rows = [
    ('building', 'LLM, RAG and AI-agent apps'),
    ('research', 'IEEE published'),
    ('working_with', 'LangGraph, Pinecone, Gemini, OpenAI, Celery'),
    ('stack', 'Python, FastAPI, React, Postgres, AWS, Azure'),
    ('reach_me', 'oahednoorforhad@gmail.com'),
]
y += 226
s, t = typed(32, y, [('$ ', GREEN), ('./status --now', TXT)], t)
b += s
for i, (k, v) in enumerate(rows):
    b += line(32, y + 30 + i * 24, [(f'{k:<14}', KEY), ('= ', DIM), (v, STR if k != 'reach_me' else CYAN)], t + 0.2 + i * 0.12)
    if k == 'building':
        b += f'<circle class="today" cx="{32 + (16 + len(v)) * 8.4 + 10:.1f}" cy="{y + 25 + i * 24}" r="3.5" fill="{ACCENT}"/>'
y += 30 + (len(rows) - 1) * 24 + 4
t += 0.3 + len(rows) * 0.12

# request trace: how one request moves through the stack. The packet loops; each stage lights as it passes.
TRACE = [('request', 'FastAPI'), ('retrieve', 'pgvector, Pinecone'), ('agent', 'LangGraph'), ('generate', 'Gemini, OpenAI'), ('observe', 'Langfuse')]
y += 52
s, t = typed(32, y, [('$ ', GREEN), ('./trace --request', TXT)], t)
b += s
y += 20
n = len(TRACE)
gap_ = 28
bw_ = (W - 64 - (n - 1) * gap_) / n
cy = y + 28
x_first, x_last = 32 + bw_ / 2, 32 + (n - 1) * (bw_ + gap_) + bw_ / 2
CYC, TRAVEL = 4.0, 75  # seconds per loop, percent of the loop spent travelling
b += f'<line x1="{x_first:.1f}" y1="{cy}" x2="{x_last:.1f}" y2="{cy}" stroke="{LINE}" stroke-width="2" class="ln" style="animation-delay:{t:.2f}s"/>'
css += (f'.pk{{animation:pk {CYC}s linear infinite}}@keyframes pk{{0%{{transform:translateX(0);opacity:1}}{TRAVEL}%{{transform:translateX({x_last - x_first:.1f}px);opacity:1}}{TRAVEL + 1}%,100%{{opacity:0;transform:translateX({x_last - x_first:.1f}px)}}}}'
        f'.lit{{opacity:0;animation:lit {CYC}s linear infinite}}')
b += (f'<g class="pk" style="animation-delay:{t + 0.6:.2f}s"><rect x="{x_first - 18:.1f}" y="{cy - 1.5}" width="18" height="3" rx="1.5" fill="{ACCENT}" opacity=".35"/>'
      f'<circle cx="{x_first:.1f}" cy="{cy}" r="4" fill="{ACCENT}"/></g>')
for i, (stage, tools) in enumerate(TRACE):
    x = 32 + i * (bw_ + gap_)
    p = TRAVEL * i / (n - 1)
    css += f'@keyframes lit{i}{{0%,{max(p - 1, 0):.1f}%{{opacity:0}}{p:.1f}%{{opacity:1}}{min(p + 14, 99):.1f}%,100%{{opacity:0}}}}'
    b += (f'<g class="ln" style="animation-delay:{t + i * 0.1:.2f}s"><rect x="{x:.1f}" y="{y}" width="{bw_:.1f}" height="56" rx="10" fill="#0f1520" stroke="{LINE}"/>'
          f'<rect class="lit" x="{x:.1f}" y="{y}" width="{bw_:.1f}" height="56" rx="10" fill="{ACCENT}" fill-opacity=".07" stroke="{ACCENT}" stroke-width="1.5" style="animation-name:lit{i};animation-delay:{t + 0.6:.2f}s"/>'
          f'<text x="{x + bw_/2:.1f}" y="{y+24}" text-anchor="middle" font-size="13" font-weight="700" fill="{STR}">{stage}</text>'
          f'<text x="{x + bw_/2:.1f}" y="{y+42}" text-anchor="middle" font-size="11" fill="{DIM}">{tools}</text></g>')
y += 56
t += 0.8

# stack
STACK = [  # (skillicons id, label, tile text if no icon). Based on recent personal + company repos' dependencies.
    ('languages', [('python', 'Python'), ('ts', 'TypeScript')]),
    ('frontend', [('react', 'React'), ('nextjs', 'Next.js'), ('vite', 'Vite'), ('tailwind', 'Tailwind'), ('tanstack', 'TanStack', 'TQ')]),
    ('backend', [('fastapi', 'FastAPI'), ('celery', 'Celery', 'Ce'), ('pydantic', 'Pydantic', 'Pd'), ('sqlalchemy', 'SQLAlchemy', 'SA')]),
    ('data', [('postgres', 'Postgres'), ('mysql', 'MySQL'), ('neon', 'Neon', 'Nn'), ('redis', 'Redis'), ('rabbitmq', 'RabbitMQ'), ('supabase', 'Supabase'), ('pgvector', 'pgvector', 'pgv')]),
    ('llms', [('gemini', 'Gemini'), ('openai', 'OpenAI'), ('cohere', 'Cohere', 'Co'), ('openrouter', 'OpenRouter', 'OR')]),
    ('agents-rag', [('langgraph', 'LangGraph', 'LG'), ('langchain', 'LangChain', 'LC'), ('aisdk', 'AI SDK', 'AI'), ('pinecone', 'Pinecone', 'Pc'), ('langfuse', 'Langfuse', 'Lf')]),
    ('cloud', [('aws', 'AWS'), ('azure', 'Azure'), ('docker', 'Docker'), ('nginx', 'Nginx'), ('vercel', 'Vercel'), ('sentry', 'Sentry')]),
]


BRAND = {'tanstack': '#ff4154', 'celery': '#6fbf4a', 'pydantic': '#e92063', 'sqlalchemy': '#d71f00', 'pgvector': '#7aa7d9', 'neon': '#00e599',
         'gemini': '#8ab4f8', 'openai': '#10a37f', 'cohere': '#ff7759', 'openrouter': '#94a3b8', 'langgraph': '#34d399',
         'langchain': '#2dd4bf', 'aisdk': '#ffffff', 'pinecone': '#6ea8fe', 'langfuse': '#f472b6', 'stripe': '#8b7bff',
         'twilio': '#f22f46', 'shopify': '#95bf47'}


SIMPLE = {  # skillicons has no icon for these: use Simple Icons glyphs on a skillicons-style dark tile
    'tanstack': ('tanstack', '#ff4154'), 'celery': ('celery', '#6fbf4a'), 'pydantic': ('pydantic', '#e92063'),
    'gemini': ('googlegemini', '#8ab4f8'), 'openai': ('openai', '#10a37f'),
    'openrouter': ('openrouter', '#94a3b8'), 'langgraph': ('langgraph', '#34d399'), 'langchain': ('langchain', '#2dd4bf'),
    'neon': ('neon', '#00e599'), 'aisdk': ('vercel', '#ffffff'),
}


def _get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=20).read().decode()


def simple_tile(slug, color):
    for url in (f'https://cdn.simpleicons.org/{slug}', f'https://cdn.jsdelivr.net/npm/simple-icons@13/icons/{slug}.svg'):
        try:
            g = _get(url)
            if '<path' not in g:
                continue
            g = re.sub(r'<svg[^>]*>', f'<svg x="60" y="60" width="136" height="136" viewBox="0 0 24 24" fill="{color}" xmlns="http://www.w3.org/2000/svg">', g, 1)
            tile = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="48" height="48"><rect width="256" height="256" rx="60" fill="#242938"/>{g}</svg>'
            return 'data:image/svg+xml;base64,' + base64.b64encode(tile.encode()).decode()
        except Exception:
            pass
    return None


_icons = {}


def icon(i):
    if i not in _icons:
        _icons[i] = _icon(i)
    return _icons[i]


def _icon(i):
    if i in SIMPLE:
        r = simple_tile(*SIMPLE[i])
        if r:
            return r
    try:
        raw = urllib.request.urlopen(urllib.request.Request(f'https://skillicons.dev/icons?i={i}&theme=dark', headers={'User-Agent': 'Mozilla/5.0'}), timeout=20).read()
        if len(raw) < 400 or b'<path' not in raw and b'<g' not in raw:
            raise ValueError('empty icon')
        return 'data:image/svg+xml;base64,' + base64.b64encode(raw).decode()
    except Exception as e:
        print('icon failed', i, e)
        return None



ROW = 42
y += 52
s, t = typed(32, y, [('$ ', GREEN), ('ls ~/stack', TXT)], t)
b += s
y += 20
for r, (grp, items) in enumerate(STACK):
    y0 = y + r * ROW
    d = t + 0.1 + r * 0.1
    b += line(32, y0 + 21, [(f'{grp}/', CYAN)], d, 13)
    x = 32 + 16 * 8.4  # same column as the status values
    for j, it in enumerate(items):
        iid, name = it[0], it[1]
        tile = it[2] if len(it) > 2 else name[:2]
        w = 6 + 22 + 7 + len(name) * 6.6 + 10
        b += f'<g class="ln" style="animation-delay:{d + 0.05 + j * 0.04:.2f}s"><rect x="{x:.1f}" y="{y0}" width="{w:.1f}" height="32" rx="8" fill="#0f1520" stroke="{LINE}"/>'
        data = icon(iid)
        if data:
            b += f'<image x="{x+6:.1f}" y="{y0+5}" width="22" height="22" href="{data}"/>'
        else:
            col = BRAND.get(iid, '#9ca3af')
            b += (f'<rect x="{x+6:.1f}" y="{y0+5}" width="22" height="22" rx="5" fill="#242938" stroke="{col}" stroke-opacity=".5"/>'
                  f'<text x="{x+17:.1f}" y="{y0+20}" text-anchor="middle" font-size="9" font-weight="700" fill="{col}">{tile}</text>')
        b += f'<text x="{x+35:.1f}" y="{y0+20}" font-size="11" fill="{KEY}">{name}</text></g>'
        x += w + 8
    assert x <= W - 24, (grp, x)
t += 0.3 + len(STACK) * 0.1
y += (len(STACK) - 1) * ROW + 32  # bottom of the last chip row

# live analytics
user = fetch_stats()
if user:
    y += 52
    s, t = typed(32, y, [('$ ', GREEN), ('gh stats ', TXT), ('--user oahednoorforhad --last 12m', STR)], t)
    b += s
    y += 20
    a, y, t = analytics(y, t + 0.2, user)
    b += a

# recent activity (loops)
events = fetch_events(4)
if events:
    y += 52
    s, t = typed(32, y, [('$ ', GREEN), ('tail -f ~/activity.log', TXT)], t)
    b += s
    a, feed_css, y, t = activity_feed(y + 28, t, events)
    b += a
    css += feed_css
    y += -18

# production checklist (all of it is in the repos above)
y += 52
s, t = typed(32, y, [('$ ', GREEN), ('./checks', TXT)], t)
b += s
b += line(32, y + 28, [('[ok] ', GREEN), ('typed async services . migrations . containers . tracing . tests . queues', DIM)], t + 0.2)
y += 28 + 32
s, t = typed(32, y, [('$ ', GREEN), ('echo ', TXT), ('"Building AI that solves real-world problems."', STR)], t + 0.4)
b += s + caret(32 + 14 * 0.6 * len('$ echo "Building AI that solves real-world problems."') + 4, y, t)
y += 37
alt = ('Terminal: Oahed Noor Forhad, AI Engineer, IEEE published researcher, building AI systems. Focus: LLMs, RAG, AI agents and real-time voice agents. '
       'Request trace: FastAPI, pgvector and Pinecone retrieval, LangGraph agent, Gemini and OpenAI generation, Langfuse observability. '
       'Stack: ' + ', '.join(x[1] for _, it in STACK for x in it) + '.')
doc = svg(y, alt, css, window(y, 'oahed@ai: ~') + b)
_delays = [float(x) for x in re.findall(r'animation-delay:([\d.]+)s', doc)]
_k = min(1.0, 3.0 / max(_delays)) if _delays else 1.0  # ponytail: linear squeeze, keeps order and stagger
doc = re.sub(r'animation-delay:([\d.]+)s', lambda m: f'animation-delay:{float(m.group(1)) * _k:.2f}s', doc)
doc = re.sub(r'begin="([\d.]+)s"', lambda m: f'begin="{float(m.group(1)) * _k:.2f}s"', doc)
print('reveal finishes at', round(max(_delays) * _k + 1.2, 1), 's (was', round(max(_delays) + 1.2, 1), 's)')
save('terminal.svg', doc)
print('ok')
