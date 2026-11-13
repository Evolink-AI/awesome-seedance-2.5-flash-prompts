#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
READMES = [
    'README.md', 'README_es.md', 'README_pt.md', 'README_ja.md', 'README_ko.md',
    'README_de.md', 'README_fr.md', 'README_tr.md', 'README_zh-TW.md',
    'README_zh-CN.md', 'README_ru.md',
]
CAMPAIGN = 'awesome-seedance-2.0-prompts'
CASE_RE = re.compile(r'^### [^:\n]+? (\d+): \[([^]]+)\]\(([^)]+)\) \([^()\n]+? \[@([^]]+)\]\(([^)]+)\)\)', re.M)
PROMPT_RE = re.compile(r'^```[^\n]*\n(.*?)\n```$', re.M | re.S)
BANNER_IMAGE_RE = re.compile(r'<img src="([^"]+)" width="900"')
MEDIA_RE = re.compile(r'<a href="([^"]+)"><img src="([^"]+)" width="300"')
DEMO_RE = re.compile(r'^\*\*\[([^]]+)\]\(([^)]+)\)\*\*.*?\[@([^]]+)\]\(([^)]+)\)', re.M)
HTTP_RE = re.compile(r'https?://[^\s)>"]+')

errors: list[str] = []
SOURCE_DATA = json.loads((ROOT / 'data/ingested_sources.json').read_text())
EXPECTED_COUNT = SOURCE_DATA.get('case_count', 0)

def check(ok: bool, message: str) -> None:
    if not ok:
        errors.append(message)


def case_prompt_blocks(text: str) -> list[str]:
    anchors = list(re.finditer(r'<a id="([a-z0-9-]+-case-\d+)"></a>', text))
    prompts: list[str] = []
    for index, anchor in enumerate(anchors):
        start = anchor.start()
        end = anchors[index + 1].start() if index + 1 < len(anchors) else len(text)
        section = text[start:end]
        matches = PROMPT_RE.findall(section)
        if matches:
            prompts.append(matches[-1])
    return prompts

def main() -> int:
    actual = sorted(p.name for p in ROOT.glob('README*.md'))
    check(actual == sorted(READMES), f'language file set mismatch: {actual}')
    texts = {name: (ROOT / name).read_text() for name in READMES if (ROOT / name).exists()}
    check(len(texts) == 11, 'all 11 README files must exist')
    if len(texts) != 11:
        return finish()

    rows = SOURCE_DATA['cases']
    demos = SOURCE_DATA['demos']
    check(SOURCE_DATA['model'] == 'Seedance 2.5 Flash', 'source index model mismatch')
    check(len(demos) == SOURCE_DATA['demo_count'], 'source index demo count mismatch')
    all_sources = [row['source_url'] for row in rows + demos]
    check(len(all_sources) == len(set(all_sources)), 'duplicate prompt or demo sources')
    expected_media = [(asset['playback_url'], asset['poster_url'])
                      for row in rows + demos for asset in row['media']]
    media_ids = [asset['id'] for row in rows + demos for asset in row['media']]
    check(len(media_ids) == len(set(media_ids)), 'duplicate source media')
    for playback, poster in expected_media:
        check(urlparse(playback).hostname == 'video.twimg.com' and
              urlparse(poster).hostname == 'pbs.twimg.com', 'unexpected source media host')
    check(urlparse(SOURCE_DATA['banner_url']).hostname == 'cdn.evolink.ai', 'unexpected banner host')

    expected_sources = None
    expected_prompts = None
    english_cases = None
    for name, text in texts.items():
        cases = CASE_RE.findall(text)
        sources = [case[2] for case in cases]
        prompts = case_prompt_blocks(text)
        banners = BANNER_IMAGE_RE.findall(text)
        gallery = text.split('<a id="demo-gallery"></a>', 1)
        prompt_media = MEDIA_RE.findall(gallery[0])
        gallery_text = gallery[1].split('<a id="contributing"></a>', 1)[0] if len(gallery) == 2 else ''
        demo_cards = list(DEMO_RE.finditer(gallery_text))
        demo_metadata = [match.groups()[1:] for match in demo_cards]
        indexed_demos = [(row['source_url'], row['author_handle'], row['author_url']) for row in demos]
        check(demo_metadata == indexed_demos, f'{name}: demo order or attribution differs from source index')
        for card, row in zip(demo_cards, demos):
            card_end = gallery_text.find('</td>', card.end())
            expected = [(asset['playback_url'], asset['poster_url']) for asset in row['media']]
            check(card_end >= 0 and MEDIA_RE.findall(gallery_text[card.end():card_end]) == expected,
                  f'{name}: media differs for {row["source_url"]}')
        check(MEDIA_RE.findall(text) == expected_media, f'{name}: media order differs from source index')
        check([poster for _, poster in prompt_media] == [row['preview_url'] for row in rows],
              f'{name}: prompt previews differ from source index')
        check(not PROMPT_RE.search(gallery_text), f'{name}: demo gallery contains a prompt block')
        if name == 'README.md':
            check([match[1] for match in demo_cards] == [row['title'] for row in demos],
                  'English demo titles differ from source index')
        anchors = re.findall(r'<a id="([a-z0-9-]+-case-\d+)"></a>', text)
        menu_links = re.findall(r'^  - \[.*?\]\(#([a-z0-9-]+-case-\d+)\)$', text, re.M)

        check(len(cases) == EXPECTED_COUNT, f'{name}: expected {EXPECTED_COUNT} cases, got {len(cases)}')
        check(len(set(sources)) == EXPECTED_COUNT, f'{name}: sources are not unique')
        check(len(prompts) == EXPECTED_COUNT, f'{name}: expected {EXPECTED_COUNT} prompt blocks, got {len(prompts)}')
        check(banners == [SOURCE_DATA['banner_url']], f'{name}: banner differs from source index')
        check(len(anchors) == EXPECTED_COUNT and anchors == menu_links, f'{name}: Menu/case anchor mismatch')
        check(not re.search(r'\| [^|\n]+ \|\n\| :----: \|\n\n\*\*[^*]+:\*\*', text), f'{name}: empty output table found')
        check('Seedance 2.5 Flash' in text and 'seedance-2-0-prompts?' not in text, f'{name}: model identity mismatch')
        check('CC BY 4.0' not in text and 'final open-source license file has not been added' not in text, f'{name}: license drift found')
        check('./public/seedance_2_prompt_images/' not in text, f'{name}: local public media reference found')
        check(not re.search(r'\b(?:TODO|TBD)\b|translation pending|translate to|\{\{[^}]+\}\}', text, re.I), f'{name}: unresolved placeholder found')
        if name != 'README.md':
            check(') or [' not in text, f'{name}: English Quick Start connector leaked into localized copy')
        check(text.find('<img src=') < text.find('## 🍌'), f'{name}: banner must be before Introduction')
        check(text.rfind('## 🙏') > text.rfind('### Case '), f'{name}: Acknowledge must follow all cases')
        for anchor in ['introduction','quick-start','menu','demo-gallery','related-repositories','contributing','license','acknowledge']:
            check(f'<a id="{anchor}"></a>' in text, f'{name}: missing section anchor {anchor}')

        if expected_sources is None:
            expected_sources, expected_prompts = sources, prompts
            english_cases = cases
        else:
            check(sources == expected_sources, f'{name}: source order differs from English')
            check(prompts == expected_prompts, f'{name}: prompt blocks differ from English')

        for url in HTTP_RE.findall(text):
            parsed = urlparse(url.rstrip('.,;'))
            if parsed.netloc not in {'evolink.ai', 'docs.evolink.ai'}:
                continue
            query = parse_qs(parsed.query)
            check(query.get('utm_source') == ['github'], f'{name}: missing utm_source on {url}')
            check(query.get('utm_campaign') == [CAMPAIGN], f'{name}: wrong utm_campaign on {url}')
            check(bool(query.get('utm_medium')) and bool(query.get('utm_content')), f'{name}: incomplete slot UTM on {url}')

    data = SOURCE_DATA
    rows = data.get('cases', [])
    check(EXPECTED_COUNT > 0 and len(rows) == EXPECTED_COUNT, f'source index case count must be {EXPECTED_COUNT}')
    check([row['source_url'] for row in rows] == expected_sources, 'source index order differs from README.md')
    check([row['title'] for row in rows] == [case[1] for case in english_cases], 'source index titles differ from README.md')
    check([row['author_handle'] for row in rows] == [case[3] for case in english_cases], 'source index author handles differ from README.md')
    check([row['author_url'] for row in rows] == [case[4] for case in english_cases], 'source index author URLs differ from README.md')
    check([row['prompt_sha256'] for row in rows] == [hashlib.sha256(prompt.encode()).hexdigest() for prompt in expected_prompts], 'source index prompt hashes differ from README.md')
    check(sum(item['count'] for item in data.get('categories', [])) == EXPECTED_COUNT, f'category counts do not sum to {EXPECTED_COUNT}')

    check([row['prompt_text'] for row in rows] == expected_prompts, 'source index prompt text differs from README.md')
    check(all(row['prompt_source_url'] == row['source_url'] for row in rows),
          'prompt source must identify its public post')
    for name in READMES:
        suffix = Path(name).stem.removeprefix('README')
        archive = f'docs/seedance-2-0{suffix}.md'
        check((ROOT / archive).is_file() and f']({archive})' in texts[name], f'{name}: missing archive link')

    required = [
        'LICENSE', 'CONTRIBUTING.md', 'CODE_OF_CONDUCT.md', 'SECURITY.md',
        'docs/maintenance.md', 'docs/update-log.md', '.github/PULL_REQUEST_TEMPLATE.md',
        '.github/ISSUE_TEMPLATE/prompt-proposal.yml', '.github/ISSUE_TEMPLATE/problem-report.yml',
    ]
    for rel in required:
        check((ROOT / rel).is_file(), f'missing required file: {rel}')

    for script, label in [
        ('tools/verify_localization.py', 'semantic localization gate'),
        ('tools/verify_star_history.py', 'Star History visibility gate'),
    ]:
        result = subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT, capture_output=True, text=True)
        check(result.returncode == 0, f'{label} failed:\n{result.stdout}{result.stderr}')
    return finish()

def finish() -> int:
    if errors:
        print('Repository verification: FAIL')
        for error in errors:
            print(f'- {error}')
        return 1
    print('Repository verification: PASS')
    print('- README files: 11')
    print(f"- Per README: {EXPECTED_COUNT} prompt cases and {SOURCE_DATA['demo_count']} demos")
    print('- Model identity: Seedance 2.5 Flash')
    print('- Media: EvoLink cover and original source posters with playback links')
    print('- Source/data equality: PASS')
    return 0

if __name__ == '__main__':
    sys.exit(main())
