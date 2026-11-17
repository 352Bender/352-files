#!/usr/bin/env python3
"""Build a static copy of the 2015 352nd VFG article site, styled like the vBulletin 4 original.

Usage: python3 build_site.py ARTICLES_XML WIDGETS_XML OUTPUT_DIR

Reads the vb1_cms export (articles.xml, widgets.xml) and writes:
  OUTPUT_DIR/index.html            front page (the "Welcome!" article)
  OUTPUT_DIR/content/<id>.html     one page per article published in 2015
  OUTPUT_DIR/section/<id>.html     one page per section, listing its articles
  OUTPUT_DIR/css/site.css
Only articles and sections that were published in 2015 are included.
Images are loaded from the GitHub Pages image host (IMG_HOST below).
"""
import html, os, re, sys, json, datetime
import xml.etree.ElementTree as ET

IMG_HOST = 'https://352bender.github.io/352-files'
FORUM_URL = 'https://www.352ndfg.com/forum'
SITE_TITLE = '352nd Virtual Fighter Group -- Il-2'

# Dropdown menu as it appeared on the live site (Wayback capture, 2016). Old content.php ids.
MENU = [
    ('The 352nd VFG', [('General Information', 144), ('The Past', 145), ('Today', 152),
                       ('Tomorrow', 159), ('Medals and Awards', 170)]),
    ('News', [('Cross-Channel Map', 213), ('Checkertails', 212), ('Happy Birthday, 352nd VFG!', 129)]),
    ('Roster', [('352nd Virtual Fighter Group Active Roster', 167), ('Deacon', 168), ('Persecutor', 169),
                ('Jinkers', 176), ("Ramblin' Jack", 178), ('Coster', 184), ('Crater', 180),
                ('TooCool', 190), ('Duckman', 192), ('Bender', 191), ('Rex', 185), ('Mike', 189),
                ('Skinny', 195), ('Wheels', 256)]),
    ('Scrapbook', [('2004 352nd Fighter Group Savannah Reunion', 241), ('Reno Air Race Photos, 2004', 226)]),
    ('Downloads', [('Cross-Channel Map', 219), ('Movies', 236), ('Fighters', 234), ('Bombers', 233)]),
    ('Technical', [("RJ's Flight Training Manual", 198)]),
    ('History', [('Christmas Day, 1944', 147), ('Hall of Honor', 174)]),
]
LEFT_WIDGETS = [33]          # Related 352nd FG Sites
FRONT_ID = 115               # "Welcome!"

NIL = '{http://www.w3.org/2001/XMLSchema-instance}nil'


def load_rows(path):
    t = open(path, encoding='utf-8', errors='replace').read()
    t = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', t)
    return [{f.get('name'): (None if f.get(NIL) == 'true' else (f.text or '')) for f in r.findall('field')}
            for r in ET.fromstring(t.encode('utf-8')).findall('row')]


# ---------- link and image rewriting ----------
def img_url(u):
    u0 = u.strip()
    m = re.match(r'^https?://(?:www\.)?352ndfg\.com(/.*)$', u0, re.I)
    if m:
        p = m.group(1)
    elif re.match(r'^[a-z]+:', u0, re.I):
        return u0
    elif u0.startswith('../'):
        p = '/' + u0[3:]
    elif u0.startswith('/'):
        p = u0
    else:
        p = '/vb/' + re.sub(r'^(\./)+', '', u0)
    p = p.replace('%5B', '[').replace('%5D', ']')
    if p == '/images/352/PageTitle/Virtual-Battles.png':
        p = '/vb/images/352/PageTitle/Virtual-Battles.png'
    return IMG_HOST + p.replace(' ', '%20').replace('[', '%5B').replace(']', '%5D')


def link_url(u, ids, depth):
    """Rewrite an href or option value to its place on the new site."""
    up = '../' * depth
    u0 = html.unescape(u.strip())
    if not u0 or u0.startswith(('#', 'mailto:', 'javascript:')):
        return u
    u0 = u0.strip('"\' ')
    m = re.search(r'content[.,/]php\?(?:r=)?(\d+)', u0)
    local = re.match(r'^(\.{0,2}/|vb/|content\.php|https?://(www\.)?352ndfg\.com/)', u0, re.I) or not re.match(r'^[a-z]+:', u0, re.I)
    if m and local:
        n = int(m.group(1))
        return f'{up}content/{n}.html' if n in ids else f'{up}index.html'
    if re.match(r'^(\./)?content\.php', u0) or re.match(r'^https?://(www\.)?352ndfg\.com/vb/content\.php', u0, re.I):
        return f'{up}index.html'
    if re.match(r'^(\./)?(showthread|forumdisplay|forum|showpost|member)\.php', u0, re.I):
        return 'https://www.352ndfg.com/vb/' + re.sub(r'^\./', '', u0)
    if re.match(r'^https?://(www\.)?352ndfg\.com/vb/(showthread|forumdisplay|forum|showpost|member)\.php', u0, re.I):
        return u0
    m = re.match(r'^(?:https?://)?(?:www\.)?352ndfg\.com(/.*)?$', u0, re.I)
    if m:
        return IMG_HOST + (m.group(1) or '/').replace(' ', '%20')
    if u0.startswith('../www.'):
        return 'http://' + u0[3:]
    if re.match(r'^www\.', u0, re.I):
        return 'http://' + u0
    if re.match(r'^[a-z]+:', u0, re.I):
        return u0
    if u0.startswith('../'):
        return IMG_HOST + '/' + u0[3:].replace(' ', '%20')
    if u0.startswith('/'):
        return IMG_HOST + u0.replace(' ', '%20')
    return IMG_HOST + '/vb/' + re.sub(r'^(\./)+', '', u0).replace(' ', '%20')


def rewrite(text, ids, depth):
    text = re.sub(r'(<img\b[^>]*?\bsrc\s*=\s*)(["\'])(.*?)\2',
                  lambda m: m.group(1) + '"' + img_url(m.group(3)) + '"', text, flags=re.I | re.S)
    text = re.sub(r'(<img\b[^>]*?\bsrc\s*=\s*)([^"\'\s>]+)',
                  lambda m: m.group(1) + '"' + img_url(m.group(2)) + '"', text, flags=re.I)
    text = re.sub(r'(<a\b[^>]*?\bhref\s*=\s*)(["\'])(.*?)\2',
                  lambda m: m.group(1) + '"' + link_url(m.group(3), ids, depth) + '"', text, flags=re.I | re.S)
    text = re.sub(r'(<option\b[^>]*?\bvalue\s*=\s*)(["\'])(.*?)\2',
                  lambda m: m.group(1) + '"' + link_url(m.group(3), ids, depth) + '"', text, flags=re.I | re.S)
    return text


# ---------- BBCode (only the tags these articles use) ----------
def bbcode(t, ids, depth):
    t = re.sub(r'\[img\](.*?)\[/img\]', lambda m: f'<img src="{html.unescape(m.group(1)).strip()}" alt="">', t, flags=re.I | re.S)
    q = r'(?:["\']|&quot;|&#39;)?'
    t = re.sub(r'\[url=' + q + r'(.*?)' + q + r'\](.*?)\[/url\]',
               lambda m: f'<a href="{html.escape(html.unescape(m.group(1)), quote=True)}">{m.group(2)}</a>', t, flags=re.I | re.S)
    t = re.sub(r'\[url\](.*?)\[/url\]',
               lambda m: f'<a href="{html.escape(html.unescape(m.group(1)), quote=True)}">{m.group(1)}</a>', t, flags=re.I | re.S)
    t = re.sub(r'\[email=["\']?(.*?)["\']?\](.*?)\[/email\]', r'<a href="mailto:\1">\2</a>', t, flags=re.I | re.S)
    t = re.sub(r'\[email\](.*?)\[/email\]', r'<a href="mailto:\1">\1</a>', t, flags=re.I | re.S)
    for tag, rep in (('b', 'strong'), ('i', 'em'), ('u', 'u')):
        t = re.sub(rf'\[{tag}\](.*?)\[/{tag}\]', rf'<{rep}>\1</{rep}>', t, flags=re.I | re.S)
    for al in ('center', 'left', 'right'):   # old pages mis-nest these, so convert each tag on its own
        t = re.sub(rf'\[{al}\]', f'<div style="text-align:{al}">', t, flags=re.I)
        t = re.sub(rf'\[/{al}\]', '</div>', t, flags=re.I)
    sizes = {'1': '10px', '2': '13px', '3': '16px', '4': '18px', '5': '24px', '6': '32px', '7': '48px'}
    t = re.sub(r'\[size=["\']?(\d)["\']?\](.*?)\[/size\]',
               lambda m: f'<span style="font-size:{sizes.get(m.group(1), "13px")}">{m.group(2)}</span>', t,
               flags=re.I | re.S)
    t = re.sub(r'\[color=["\']?([#\w]+)["\']?\](.*?)\[/color\]', r'<span style="color:\1">\2</span>', t,
               flags=re.I | re.S)
    t = re.sub(r'\[hr\]\s*(\[/hr\])?', '<hr>', t, flags=re.I)
    t = re.sub(r'\[attach[^\]]*\].*?\[/attach\]', '', t, flags=re.I | re.S)  # vB4 attachments were not exported
    t = re.sub(r'\[/?v\]', '', t, flags=re.I)
    return t


def render_body(row, ids, depth):
    t = row['pagetext'] or ''
    state = row.get('htmlstate') or 'off'
    if state == 'off':
        t = html.escape(t)
    t = bbcode(t, ids, depth)
    t = rewrite(t, ids, depth)
    if state in ('off', 'on_nl2br'):
        t = t.replace('\r\n', '\n').replace('\n', '<br>\n')
    # drop the old spam-protection email scripts (document.write); they no longer work
    t = re.sub(r'<script\b[\s\S]*?</script>', '', t, flags=re.I)
    return t


def preview(row, n=300):
    t = re.sub(r'\[/?[a-z]+[^\]]*\]', ' ', row['pagetext'] or '', flags=re.I)
    t = re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>', ' ', t, flags=re.I)
    t = html.unescape(re.sub(r'<[^>]+>', ' ', t))
    t = re.sub(r'\s+', ' ', t).strip()
    return html.escape(t[:n] + ('...' if len(t) > n else ''))


def fmt_date(ts):
    try:
        return datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).strftime('%m-%d-%Y')
    except (TypeError, ValueError):
        return ''


# ---------- page shell ----------
def page(title, crumbs, center, left, right, depth):
    up = '../' * depth
    menu = []
    for label, items in MENU:
        sub = ''.join(f'<li><a href="{up}content/{i}.html">{html.escape(t)}</a></li>' for t, i in items)
        menu.append(f'<li class="drop"><a href="#" class="dropctrl">{html.escape(label)}</a><ul>{sub}</ul></li>')
    crumb_html = f'<a href="{up}index.html">Home</a>' + ''.join(
        f' &rsaquo; <a href="{up}{h}">{html.escape(t)}</a>' if h else f' &rsaquo; {html.escape(t)}'
        for t, h in crumbs)
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>{html.escape(SITE_TITLE)} - {html.escape(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="{up}css/site.css">
</head><body>
<div class="above_body"><div id="header"><a href="{up}index.html"><img class="logo" src="{IMG_HOST}/vb/images/352/forum/title/title1.png" alt="352nd Virtual Fighter Group" width="544" height="150"></a></div>
<div class="navbar">
<ul class="navtabs"><li class="selected"><a href="{up}index.html">Articles</a></li><li><a href="{FORUM_URL}">Forum</a></li></ul>
<ul class="navlinks">{''.join(menu)}<li><a href="{IMG_HOST}/Y-29/main.htm">Y-29</a></li></ul>
</div></div>
<div class="body_wrapper">
<div id="breadcrumb">{crumb_html}</div>
<div class="notices">Restored copy of the 352nd VFG article site as it stood in January 2015. Rosters, ranks and dates are from that time.</div>
<div class="layout">
<div class="col left">{left}</div>
<div class="col main">{center}</div>
<div class="col right">{right}</div>
</div></div>
<div id="footer"><a href="{up}index.html">352nd Virtual Fighter Group (IL-2)</a> &middot; <a href="{FORUM_URL}">Forum</a> &middot; <a href="#">Top</a></div>
<p class="copyright">352nd Virtual Fighter Group &middot; content 2000&ndash;2015</p>
<script>
document.querySelectorAll('.dropctrl').forEach(function(a){{a.addEventListener('click',function(e){{e.preventDefault();var li=a.parentNode,open=li.classList.contains('open');document.querySelectorAll('.drop.open').forEach(function(x){{x.classList.remove('open')}});if(!open)li.classList.add('open');}});}});
document.addEventListener('click',function(e){{if(!e.target.closest('.drop'))document.querySelectorAll('.drop.open').forEach(function(x){{x.classList.remove('open')}});}});
</script>
</body></html>
'''


def widget(title, body):
    return f'<div class="cms_widget"><div class="cms_widget_header"><h3>{html.escape(title)}</h3></div><div class="cms_widget_content">{body}</div></div>'


CSS = '''
html{background:#e9e9e9 url("IMG/vb/images/352/forum/background.gif")}
body{margin:0;font:13px Tahoma,Calibri,Verdana,Geneva,sans-serif;color:#3e3e3e}
a{color:#417394;text-decoration:none}a:hover{color:#417394;text-decoration:underline}
.above_body{background:url("IMG/vb/images/352/forum/title/19.png") repeat-x;height:205px;position:relative;min-width:980px}
#header{height:150px}#header .logo{display:block}
.navbar{position:absolute;left:10px;right:10px;bottom:4px;background:#6b8fae;border:1px solid #333;font:11px Arial,Calibri,Verdana,Geneva,sans-serif}
.navtabs{list-style:none;margin:0;padding:0 0 0 20px;height:26px;background:#4e687f}
.navtabs li{float:left;margin-right:2px}
.navtabs li a{display:block;height:22px;padding:4px 10px 0;color:#fff;font-size:12px}
.navtabs li.selected a{background:#7192a8;border-top:1px solid #cedfeb;color:#000;font-weight:bold}
.navlinks{list-style:none;margin:0;padding:0 0 0 10px;height:26px;background:#7192a8}
.navlinks>li{float:left;position:relative}
.navlinks>li>a{display:block;padding:6px 8px;color:#fff}
.navlinks .drop>a:after{content:" \\25BE"}
.navlinks ul{display:none;position:absolute;left:0;top:26px;z-index:10;list-style:none;margin:0;padding:0;background:#fff;border:1px solid #6b8fae;min-width:230px;box-shadow:2px 2px 4px rgba(0,0,0,.3)}
.navlinks .drop.open ul,.navlinks .drop:hover ul{display:block}
.navlinks ul a{display:block;padding:5px 10px;color:#3e3e3e;border-bottom:1px solid #eee;font-size:12px}
.navlinks ul a:hover{background:#ffeb90;text-decoration:none}
.body_wrapper{padding:10px 20px}
#breadcrumb{margin:0 0 8px}
.notices{background:#ffeb90;padding:5px 10px;font-size:12px;margin-bottom:10px}
.layout{display:flex;gap:20px;align-items:flex-start}
.col.left{flex:0 0 220px}.col.right{flex:0 0 220px}.col.main{flex:1;min-width:0}
.cms_widget{background:#f1f1f1;border:1px solid #c1c1c1;margin-bottom:10px;padding:0 6px 6px}
.cms_widget_header h3{margin:0;padding:4px 6px 2px;font-size:13px;color:#424242;text-align:center}
.cms_widget_content{background:#fff;border:1px solid #dadada;padding:10px 6px;color:#424242;font-size:12px}
.cms_widget_content ul{margin:0;padding-left:16px}.cms_widget_content li{margin:3px 0}
h1.article_title{font:20px Georgia,serif;color:#425769;border-top:4px solid #425769;border-bottom:1px dotted #425769;padding:5px 10px;margin:0 0 6px}
.meta{font-size:11px;color:#777;padding:0 10px 8px}
.article{text-align:justify;padding:0 10px;overflow-x:auto}
.article img{max-width:100%;height:auto}
.article table img{max-width:none}
.preview{border:1px solid #b2b2b2;background:#fff;padding:8px 10px;margin-bottom:10px}
.preview h2{font:16px Georgia,serif;margin:0 0 4px}
.preview .more{font-size:11px;font-weight:bold}
table.roster{border-collapse:collapse;width:100%}
td.roster,td.plain{border:1px solid #000;padding:6.5px;vertical-align:middle}
td.plain table td.plain{border:1px solid #ddd}
.dropshadow{box-shadow:3px 3px 4px rgba(0,0,0,.35)}
.imgcenter{display:block;margin:auto}
.title352,.storytitle{font:bold 18px Georgia,serif;color:#425769;text-align:center;margin:6px 0}
#footer{background:#6b8fae;border-top:1px solid #425769;border-bottom:1px solid #425769;padding:5px 20px;text-align:right;margin:10px 20px 0}
#footer a{color:#fff;margin-left:6px}
.copyright{text-align:center;font-size:11px;color:#666}
@media (max-width:900px){.layout{flex-direction:column}.col.left,.col.right{flex:none;width:100%}.above_body{min-width:0}}
'''


def main(articles_xml, widgets_xml, out):
    rows = load_rows(articles_xml)
    by = {r['nodeid']: r for r in rows}

    def visible(r):  # published in 2015, and every ancestor section published too
        while r:
            if r['setpublish'] != '1':
                return False
            r = by.get(r['parentnode'])
        return True

    arts = [r for r in rows if r['issection'] == '0' and visible(r)]
    secs = [r for r in rows if r['issection'] == '1' and visible(r) and r['nodeid'] != '1']
    ids = {int(r['nodeid']) for r in arts}
    kids = {}
    for r in arts + secs:
        kids.setdefault(r['parentnode'], []).append(r)
    for v in kids.values():
        v.sort(key=lambda r: int(r['nodeleft']))

    # widgets
    wrows = load_rows(widgets_xml)
    wid = {}
    for w in wrows:
        if w.get('name') == 'statichtml':
            wid[int(w['widgetid'])] = (w['title'], w['value'] or '')

    def left_col(depth):
        parts = []
        for i in LEFT_WIDGETS:
            if i in wid:
                title, body = wid[i]
                body = re.sub(r'\s(onMouse\w+)="[^"]*"', '', body)
                parts.append(widget(title, rewrite(body, ids, depth)))
        up = '../' * depth
        tree = []

        def walk(pid, lvl):
            for s in [x for x in kids.get(pid, []) if x['issection'] == '1']:
                tree.append(f'<li style="margin-left:{lvl * 10}px"><a href="{up}section/{s["nodeid"]}.html">{s["title"]}</a></li>')
                walk(s['nodeid'], lvl + 1)
        walk('1', 0)
        parts.append(widget('Sections', '<ul>' + ''.join(tree) + '</ul>'))
        return ''.join(parts)

    recent = sorted(arts, key=lambda r: -int(r['publishdate'] or 0))[:8]

    def right_col(depth):
        up = '../' * depth
        items = ''.join(f'<li><a href="{up}content/{r["nodeid"]}.html">{r["title"]}</a><br><small>{fmt_date(r["publishdate"])}</small></li>'
                        for r in recent)
        return widget('Latest Articles', '<ul>' + items + '</ul>')

    def crumbs_for(r, depth, include_self):
        chain = []
        p = by.get(r['parentnode'])
        while p and p['nodeid'] != '1':
            chain.append((html.unescape(p['title']), f'section/{p["nodeid"]}.html'))
            p = by.get(p['parentnode'])
        chain.reverse()
        if include_self:
            chain.append((html.unescape(r['title']), None))
        return chain

    os.makedirs(os.path.join(out, 'content'), exist_ok=True)
    os.makedirs(os.path.join(out, 'section'), exist_ok=True)
    os.makedirs(os.path.join(out, 'css'), exist_ok=True)
    open(os.path.join(out, 'css', 'site.css'), 'w').write(CSS.replace('IMG', IMG_HOST))

    def article_html(r, depth):
        return (f'<h1 class="article_title">{r["title"]}</h1>'
                f'<div class="meta">Published {fmt_date(r["publishdate"])}</div>'
                f'<div class="article">{render_body(r, ids, depth)}</div>')

    for r in arts:
        title = html.unescape(r['title'])
        open(os.path.join(out, 'content', f'{r["nodeid"]}.html'), 'w').write(
            page(title, crumbs_for(r, 1, True), article_html(r, 1), left_col(1), right_col(1), 1))

    for s in secs:
        items = [x for x in kids.get(s['nodeid'], [])]
        body = [f'<h1 class="article_title">{s["title"]}</h1>']
        for x in items:
            if x['issection'] == '1':
                body.append(f'<div class="preview"><h2><a href="../section/{x["nodeid"]}.html">{x["title"]}</a></h2><span class="more">Section</span></div>')
            else:
                body.append(f'<div class="preview"><h2><a href="../content/{x["nodeid"]}.html">{x["title"]}</a></h2>'
                            f'<div class="meta">Published {fmt_date(x["publishdate"])}</div>{preview(x)} '
                            f'<a class="more" href="../content/{x["nodeid"]}.html">Read more</a></div>')
        if len(body) == 1:
            body.append('<p>There are no articles in this section.</p>')
        open(os.path.join(out, 'section', f'{s["nodeid"]}.html'), 'w').write(
            page(html.unescape(s['title']), crumbs_for(s, 1, True), ''.join(body), left_col(1), right_col(1), 1))

    front = by[str(FRONT_ID)]
    open(os.path.join(out, 'index.html'), 'w').write(
        page('The Front Page', [('The Front Page', None)],
             f'<h1 class="article_title">The Front Page</h1><div class="article">{render_body(front, ids, 0)}</div>',
             left_col(0), right_col(0), 0))

    missing = [i for _, items in MENU for _, i in items if i not in ids]
    print(f'{len(arts)} article pages, {len(secs)} section pages, front page written to {out}')
    if missing:
        print('Menu entries with no page (left as dead links):', missing)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
