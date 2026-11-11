#!/usr/bin/env python3
"""차 노트 데이터 도구 — 내용을 넣을 때 서식을 지키게 돕는다. 규칙 설명은 docs/content-rules.md.

  python3 tools/tea.py check                      형식 검사(올리기 전에 꼭 돌린다)
  python3 tools/tea.py next                       다음에 쓸 번호(t…, g…)
  python3 tools/tea.py photo gimul 원본 [이름]      기물 사진 → assets/gimul/이름.jpg + 썸네일
  python3 tools/tea.py photo tasting 원본 t108 1   시음노트 사진 → assets/tasting-t108-1.jpg

파이썬에서 고칠 때:
  import sys; sys.path.insert(0, 'tools'); import tea
  d = tea.load()          # d.lessons(수업노트+연대기) · d.tastings · d.gimul
  ...고친다...
  tea.save(d)             # index.html의 데이터 줄만 다시 쓴다(다른 줄은 그대로)
"""
import html, json, os, re, sys
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'index.html')
ASSETS = os.path.join(ROOT, 'assets')

LESSON_RE = re.compile(r'window\.__TEA_LESSONS=\(window\.__TEA_LESSONS\|\|\[\]\)\.concat\(')
TASTING_KEY = 'window.__TEA_TASTINGS='
GIMUL_KEY = 'window.__TEA_GIMUL='

CLAYS = ['자니', '주니', '홍니', '단니', '백자', '기타', '미분류']   # 이 순서로 묶어 보여 준다
GIMUL_TYPES = ['차호', '잔', '기타']
CRAFTS = ['전수공', '반수공', '']
SEASONS = ['봄', '여름', '가을', '겨울', '']
SORTS = ['생차', '숙차', '우롱', '백차', '홍차', '녹차', '황차', '흑차']
GRADES = ['고수', '단주', '단주급', '국유림', '차왕수', '황편', '']


def _dump(v):
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'))


def esc(text):
    """보통 글 → 데이터의 html 칸에 넣을 글(&, <, >, 따옴표를 바꾼다)."""
    return html.escape(str(text), quote=True)


def load(path=INDEX):
    """index.html에서 데이터를 읽는다."""
    t = open(path, encoding='utf8').read()
    dec = json.JSONDecoder()
    spans = []      # (시작, 끝, 종류)
    lessons = []
    for m in LESSON_RE.finditer(t):
        v, n = dec.raw_decode(t[m.end():])
        spans.append((m.end(), m.end() + n, 'lesson', len(v)))
        lessons += v
    out = {}
    for name, key in (('tastings', TASTING_KEY), ('gimul', GIMUL_KEY)):
        i = t.index(key) + len(key)
        v, n = dec.raw_decode(t[i:])
        spans.append((i, i + n, name, None))
        out[name] = v
    return SimpleNamespace(lessons=lessons, tastings=out['tastings'], gimul=out['gimul'], _text=t, _spans=spans)


def save(d, path=INDEX):
    """데이터 줄만 다시 쓴다. 수업노트는 문서(Part)마다 한 줄씩이고, 줄 수가 달라졌으면 lesson_script()로 줄을 먼저 넣는다."""
    t = d._text
    lesson_spans = [s for s in d._spans if s[2] == 'lesson']
    if sum(s[3] for s in lesson_spans) != len(d.lessons):
        raise SystemExit('수업노트 문서 수가 달라졌습니다. 새 Part는 lesson_script()가 만든 줄을 index.html에 Part 번호 순서대로 넣은 뒤 다시 load() 하세요.')
    parts, k = [], 0
    for s in lesson_spans:
        parts.append((s[0], s[1], _dump(d.lessons[k:k + s[3]])))
        k += s[3]
    for s in d._spans:
        if s[2] == 'tastings':
            parts.append((s[0], s[1], _dump(d.tastings)))
        if s[2] == 'gimul':
            parts.append((s[0], s[1], _dump(d.gimul)))
    for a, b, text in sorted(parts, reverse=True):
        t = t[:a] + text + t[b:]
    open(path, 'w', encoding='utf8').write(t)
    d._text = t


def lesson_script(doc):
    """새 Part 하나를 index.html에 넣을 두 줄(<script>…</script>)을 만든다."""
    return '<script>window.__TEA_LESSONS=(window.__TEA_LESSONS||[]).concat(' + _dump([doc]) + ');\n</script>\n'


def next_id(items, prefix):
    return prefix + str(max(int(x['id'][len(prefix):]) for x in items) + 1)


def sort_gimul(items):
    """기물 배열 순서: 흙 순서 → 이름 가나다순."""
    items.sort(key=lambda x: (CLAYS.index(x['clay']) if x['clay'] in CLAYS else len(CLAYS), x['label']))


# ---------------------------------------------------------------- 검사

P_ALLOWED = re.compile(r'</?(?:b|i)>|<span class="mark-green">|</span>')
T_ALLOWED = re.compile(r'</?(?:table|tr|th|td|div|b|i)>|<div class="cell-src">|<span class="mark-green">|</span>')
ENTITY = re.compile(r'&(?:amp|lt|gt|quot|#x27|#39);')


def _html_problems(s, allowed):
    rest = allowed.sub('', s)
    probs = []
    if '<' in rest or '>' in rest:
        probs.append('허용하지 않는 태그나 바꾸지 않은 < > 가 있음')
    if '&' in ENTITY.sub('', rest):
        probs.append('바꾸지 않은 & 가 있음(&amp;로)')
    if re.search(r'<b>\s*<b>|<i>\s*<i>|<b>\s*</b>|<i>\s*</i>', s):
        probs.append('굵게·기울임 태그가 겹치거나 비어 있음')
    for tag in ('b', 'i', 'span', 'div', 'td', 'th', 'tr', 'table'):
        if len(re.findall(r'<%s[ >]' % tag, s)) != s.count('</%s>' % tag):
            probs.append('<%s> 열고 닫는 수가 다름' % tag)
    return probs


def check(d=None, verbose=True):
    d = d or load()
    errors, warns = [], []
    E = lambda where, msg: errors.append('%s: %s' % (where, msg))
    W = lambda where, msg: warns.append('%s: %s' % (where, msg))

    def text_ok(where, s):
        if s != s.strip():
            E(where, '앞뒤에 빈칸이 있음')
        if '\n' in s or '\t' in s:
            E(where, '줄바꿈·탭 글자가 들어 있음')
        if '  ' in s:
            W(where, '빈칸이 두 개 이어져 있음')

    ids = [x['id'] for x in d.lessons + d.tastings + d.gimul]
    for i in set(ids):
        if ids.count(i) > 1:
            E(i, '같은 id가 여러 개')

    # ---- 수업노트 · 연대기
    for doc in d.lessons:
        w = doc.get('id', '?')
        if sorted(doc.keys()) != ['blocks', 'id', 'label']:
            E(w, '문서 칸은 id·label·blocks 세 개여야 함')
        if w != 'chr' and not re.fullmatch(r'p\d+', w):
            E(w, "수업노트 id는 'p' + Part 번호")
        if w != 'chr' and not re.fullmatch(r'\S+ Part\.\d+', doc.get('label', '')):
            W(w, "label은 '보이차 Part.7'처럼 '주제 Part.번호' 꼴")
        bl = doc.get('blocks', [])
        if not bl or bl[0].get('k') != 'h1':
            E(w, '첫 블록은 h1(강 제목)이어야 함')
        for n, b in enumerate(bl):
            at = '%s #%d(%s)' % (w, n, b.get('k'))
            k = b.get('k')
            if k in ('h1', 'h2', 'h3', 'h4'):
                if sorted(b.keys()) != ['k', 'text']:
                    E(at, '제목 블록은 k·text만')
                    continue
                text_ok(at, b['text'])
                if '<' in b['text'] or '&amp;' in b['text']:
                    E(at, '제목 text는 보통 글 그대로(태그·&amp; 없이)')
                if w != 'chr' and k == 'h2' and not re.match(r'[□※] \S', b['text']):
                    E(at, "소제목(h2)은 '□ ' 또는 '※ '로 시작: " + b['text'][:30])
                if w != 'chr' and k == 'h1' and not re.fullmatch(r'\d+강|\d+ & \d+강|부록 — .+', b['text']):
                    W(at, "강 제목이 '3강' · '1 & 2강' · '부록 — …' 꼴이 아님: " + b['text'][:30])
            elif k == 'p':
                if sorted(b.keys()) != ['bul', 'html', 'ind', 'k']:
                    E(at, 'p 블록은 k·html·ind·bul 네 칸')
                    continue
                text_ok(at, b['html'])
                if b['ind'] not in (0, 22, 25, 40, 56):
                    E(at, 'ind는 0·22·40·56(인용문만 25) 중 하나: %r' % b['ind'])
                if not isinstance(b['bul'], bool):
                    E(at, 'bul은 true/false')
                elif b['ind'] == 0 and b['bul']:
                    E(at, 'ind 0(서술 문단)에는 글머리 점을 붙이지 않음')
                if b['ind'] == 25 and not b['html'].startswith('<i>'):
                    E(at, 'ind 25는 <i>로 감싼 인용문에만')
                if b['html'].lstrip().startswith('※'):
                    E(at, "'※' 메모는 p가 아니라 note 블록으로")
                for msg in _html_problems(b['html'], P_ALLOWED):
                    E(at, msg + ': ' + b['html'][:40])
            elif k == 'note':
                keys = sorted(b.keys())
                if keys not in (['html', 'k'], ['bul', 'html', 'ind', 'k']):
                    E(at, 'note 블록은 k·html (+ ind·bul)')
                    continue
                text_ok(at, b['html'])
                if not b['html'].startswith('※ '):
                    E(at, "메모(note)는 '※ '로 시작: " + b['html'][:30])
                if 'ind' in b and (b['ind'] not in (14, 22, 40) or b['bul'] is not False):
                    E(at, 'note의 ind는 14·22·40, bul은 false')
                for msg in _html_problems(b['html'], P_ALLOWED):
                    E(at, msg + ': ' + b['html'][:40])
            elif k == 'table':
                if sorted(b.keys()) != ['html', 'k']:
                    E(at, 'table 블록은 k·html만')
                    continue
                h = b['html']
                if not (h.startswith('<table><tr><th><div><b>') and h.endswith('</tr></table>')):
                    E(at, '표는 <table><tr><th><div><b>머리</b></div></th>… 꼴')
                for msg in _html_problems(h, T_ALLOWED):
                    E(at, msg)
                rows = re.findall(r'<tr>(.*?)</tr>', h)
                cols = [len(re.findall(r'<t[hd]>', r)) for r in rows]
                if len(set(cols)) > 1:
                    E(at, '표의 줄마다 칸 수가 다름: %s' % cols)
                if re.search(r'<td>(?!<div|</td>)|<th>(?!<div><b>)', h):
                    E(at, '칸 안의 글은 <div>…</div>로 감쌈(머리칸은 <div><b>…</b></div>, 빈칸은 <td></td>)')
            else:
                E(at, '모르는 블록 종류: %r' % k)

    # ---- 시음노트
    keys_t = ['blocks', 'grade', 'id', 'images', 'kind', 'label', 'price', 'season', 'sort', 'unit', 'year']
    for x in d.tastings:
        w = x.get('id', '?') + ' ' + x.get('label', '')
        if sorted(x.keys()) != keys_t:
            E(w, '시음노트 칸이 정해진 11개와 다름')
            continue
        if not re.fullmatch(r't\d+', x['id']) or x['kind'] != 'tasting':
            E(w, "id는 t+번호, kind는 'tasting'")
        text_ok(w, x['label'])
        if not x['label']:
            E(w, '이름(label)이 비어 있음')
        if not re.fullmatch(r'(\d{4})?', x['year']):
            E(w, "year는 '2026'처럼 숫자 4자리(모르면 빈칸): %r" % x['year'])
        if x['season'] not in SEASONS:
            E(w, 'season은 봄·여름·가을·겨울(모르면 빈칸): %r' % x['season'])
        if x['sort'] not in SORTS:
            W(w, '처음 보는 다류(sort): %r' % x['sort'])
        if x['grade'] not in GRADES:
            W(w, '처음 보는 등급(grade): %r' % x['grade'])
        if not re.fullmatch(r'(\d+(\.\d+)?g)?', x['unit']):
            E(w, "unit은 '100g'처럼 숫자+g(모르면 빈칸): %r" % x['unit'])
        if x['price'] and not re.match(r'\d+(\.\d+)?만 원', x['price']):
            W(w, "price가 '58만 원'으로 시작하지 않아 100g당 값이 계산되지 않음: %r" % x['price'])
        if bool(x['price']) != bool(x['unit']):
            W(w, 'price와 unit은 둘 다 적거나 둘 다 비움(한쪽만 있으면 100g당 값이 계산되지 않음)')
        bl = x['blocks']
        if not bl or bl[0] != {'k': 'h1', 'text': '테이스팅 기록'}:
            E(w, "첫 블록은 {k:h1, text:'테이스팅 기록'}")
        for n, b in enumerate(bl[1:], 1):
            at = '%s #%d' % (w, n)
            if b.get('k') == 'p':
                if sorted(b.keys()) != ['bul', 'html', 'ind', 'k'] or b['ind'] != 22 or b['bul'] is not True:
                    E(at, '기록 한 줄은 {k:p, html, ind:22, bul:true}')
            elif b.get('k') == 'note':
                if sorted(b.keys()) != ['html', 'k'] or not b['html'].startswith('※ '):
                    E(at, "메모는 {k:note, html:'※ …'}")
            else:
                E(at, '시음노트 블록은 p와 note만')
            if 'html' in b:
                text_ok(at, b['html'])
                for msg in _html_problems(b['html'], P_ALLOWED):
                    E(at, msg + ': ' + b['html'][:40])
        for n, f in enumerate(x['images'], 1):
            if f != 'tasting-%s-%d.jpg' % (x['id'], n):
                E(w, '사진 이름은 tasting-%s-%d.jpg 차례: %r' % (x['id'], n, f))
            if not os.path.isfile(os.path.join(ASSETS, f)):
                E(w, '사진 파일이 없음: assets/' + f)

    # ---- 기물노트
    keys_g = ['artist', 'blocks', 'clay', 'craft', 'id', 'images', 'kind', 'label', 'price', 'shape', 'type']
    for x in d.gimul:
        w = x.get('id', '?') + ' ' + x.get('label', '')
        if sorted(x.keys()) != keys_g:
            E(w, '기물 칸이 정해진 11개와 다름')
            continue
        if not re.fullmatch(r'g\d+', x['id']) or x['kind'] != 'gimul':
            E(w, "id는 g+번호, kind는 'gimul'")
        text_ok(w, x['label'])
        text_ok(w, x['artist'])
        text_ok(w, x['price'])
        if not x['label']:
            E(w, '이름(label)이 비어 있음')
        if x['clay'] not in CLAYS:
            E(w, 'clay(흙)는 %s 중 하나: %r' % ('·'.join(CLAYS), x['clay']))
        if x['craft'] not in CRAFTS:
            E(w, "craft(제작)는 전수공·반수공 중 하나(모르면 빈칸): %r" % x['craft'])
        if re.search(r'[()（）]', x['label']):
            E(w, '기물 제목에는 괄호를 쓰지 않음(시대·구별 말은 맨 앞에, 전수공·반수공은 craft 칸에)')
        if re.search(r'전수공|반수공', x['label']):
            E(w, '전수공·반수공은 제목이 아니라 craft 칸에 적음')
        text_ok(w, x['shape'])
        if x['shape'] and x['shape'] not in x['label']:
            W(w, 'shape(기형)이 제목에 들어 있지 않음: %r' % x['shape'])
        if x['type'] not in GIMUL_TYPES:
            E(w, 'type(종류)은 %s 중 하나: %r' % ('·'.join(GIMUL_TYPES), x['type']))
        if x['price'] and not re.search(r'\d만 원', x['price']):
            W(w, "가격에는 '350만 원'처럼 숫자+'만 원'(띄어 씀)이 들어가야 함: %r" % x['price'])
        if re.search(r'\d만원|만 원(?=[가-힣])(?!대)', x['price']):
            W(w, "'만 원' 뒤의 덧말은 띄어 씀('280만 원 정도'): %r" % x['price'])
        bl = x['blocks']
        if bl:
            if bl[0] != {'k': 'h1', 'text': '특징'}:
                E(w, "특징이 있으면 첫 블록은 {k:h1, text:'특징'}")
            if len(bl) == 1:
                E(w, "특징 줄이 없으면 blocks는 []")
            for n, b in enumerate(bl[1:], 1):
                at = '%s #%d' % (w, n)
                if sorted(b.keys()) != ['bul', 'html', 'ind', 'k'] or b['k'] != 'p' or b['ind'] != 22 or b['bul'] is not True:
                    E(at, '특징 한 줄은 {k:p, html, ind:22, bul:true}')
                    continue
                text_ok(at, b['html'])
                for msg in _html_problems(b['html'], P_ALLOWED):
                    E(at, msg + ': ' + b['html'][:40])
        for f in x['images']:
            if ' ' in f or '/' in f or not f.endswith('.jpg'):
                E(w, '사진 이름은 빈칸·/ 없이 .jpg: %r' % f)
            for sub in ('gimul', os.path.join('gimul', 't')):
                if not os.path.isfile(os.path.join(ASSETS, sub, f)):
                    E(w, '사진 파일이 없음: assets/%s/%s' % (sub.replace(os.sep, '/'), f))
    want = sorted(d.gimul, key=lambda x: (CLAYS.index(x['clay']) if x['clay'] in CLAYS else 99, x['label']))
    if [x['id'] for x in want] != [x['id'] for x in d.gimul]:
        E('기물노트', '배열 순서가 흙 순서 → 이름 가나다순이 아님(tea.sort_gimul로 정렬)')

    # ---- 사진 파일
    used = set('assets/' + f for x in d.tastings for f in x['images'])
    used |= set('assets/gimul/' + f for x in d.gimul for f in x['images'])
    try:
        from PIL import Image
    except ImportError:
        Image = None
        W('사진', 'PIL(pillow)이 없어 사진 크기·위치 정보 검사를 건너뜀')
    for base, sub in ((ASSETS, ''), (os.path.join(ASSETS, 'gimul'), 'gimul/')):
        for f in sorted(os.listdir(base)):
            full = os.path.join(base, f)
            if not os.path.isfile(full):
                continue
            rel = 'assets/' + sub + f
            if rel not in used:
                W(rel, '어느 글에도 쓰이지 않는 사진')
            if Image:
                im = Image.open(full)
                if max(im.size) > 1000:
                    E(rel, '긴 변이 1000px보다 큼: %dx%d' % im.size)
                if len(im.getexif()):
                    E(rel, '사진에 EXIF(위치 정보 등)가 남아 있음')

    if verbose:
        for m in errors:
            print('오류  ' + m)
        for m in warns:
            print('주의  ' + m)
        print('수업노트 %d편 · 연대기 %d · 시음노트 %d개 · 기물 %d점 — 오류 %d, 주의 %d' % (
            sum(1 for x in d.lessons if x['id'] != 'chr'), sum(1 for x in d.lessons if x['id'] == 'chr'),
            len(d.tastings), len(d.gimul), len(errors), len(warns)))
    return errors, warns


# ---------------------------------------------------------------- 사진

def _shrink(src, dst, long_side, quality):
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(src)).convert('RGB')
    im.thumbnail((long_side, long_side), Image.LANCZOS)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im.save(dst, 'JPEG', quality=quality, progressive=True, optimize=True)   # exif를 넘기지 않으므로 위치 정보가 지워진다
    assert not len(Image.open(dst).getexif())
    return im.size


def photo_gimul(src, name=None):
    """기물 사진 한 장을 줄여 넣고, images에 적을 파일 이름을 돌려준다."""
    name = (name or os.path.splitext(os.path.basename(src))[0]).replace(' ', '_')
    name = re.sub(r'\.jpe?g$', '', name, flags=re.I) + '.jpg'
    big = os.path.join(ASSETS, 'gimul', name)
    if os.path.exists(big):
        raise SystemExit('같은 이름의 사진이 이미 있습니다: ' + name)
    _shrink(src, big, 1000, 80)
    _shrink(src, os.path.join(ASSETS, 'gimul', 't', name), 200, 78)
    return name


def photo_tasting(src, tid, n):
    """시음노트 사진 한 장을 줄여 넣고, images에 적을 파일 이름을 돌려준다."""
    name = 'tasting-%s-%d.jpg' % (tid, int(n))
    dst = os.path.join(ASSETS, name)
    if os.path.exists(dst):
        raise SystemExit('같은 이름의 사진이 이미 있습니다: ' + name)
    _shrink(src, dst, 1000, 80)
    return name


def main(argv):
    if len(argv) >= 1 and argv[0] == 'check':
        errors, _ = check()
        return 1 if errors else 0
    if len(argv) >= 1 and argv[0] == 'next':
        d = load()
        print('다음 시음노트 번호:', next_id(d.tastings, 't'))
        print('다음 기물 번호:', next_id(d.gimul, 'g'))
        print('지금 있는 Part:', ', '.join(x['label'] for x in d.lessons if x['id'] != 'chr'))
        return 0
    if len(argv) >= 3 and argv[0] == 'photo' and argv[1] == 'gimul':
        print(photo_gimul(argv[2], argv[3] if len(argv) > 3 else None))
        return 0
    if len(argv) == 5 and argv[0] == 'photo' and argv[1] == 'tasting':
        print(photo_tasting(argv[2], argv[3], argv[4]))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
