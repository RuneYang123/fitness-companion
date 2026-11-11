#!/usr/bin/env python3
"""Validate public project files and build local distribution archives.

Python standard library only. No network, model calls, health-data collection,
installation, Git staging, or publication. The default archive contains only
the Skill; --repository also exports the approved repository files.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'fitness-companion'
EXCLUDED = {'dist', '.git', '__pycache__', '.DS_Store'}
ROOT_FILES = {'README.md', 'LICENSE', 'NOTICE.md', '.gitignore', 'CONTRIBUTING.md', 'CHANGELOG.md'}
REPOSITORY_FILES = {
    'docs/publishing.md', 'scripts/package.py', 'tests/test_package.py',
    '.github/ISSUE_TEMPLATE/bug_report.yml',
    '.github/ISSUE_TEMPLATE/feature_request.yml',
    '.github/PULL_REQUEST_TEMPLATE.md', '.github/workflows/validate.yml',
}
ALLOWED_EXTENSIONS = {'.md', '.py', '.yaml', '.yml'}
REPOSITORY_URL = 'https://github.com/RuneYang123/fitness-companion'
CONTACT_EMAIL = 'runeyang123@outlook.com'


def is_icon(path):
    return path == SKILL / 'assets' / 'fitness-companion-icon-v1.png'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def public_files():
    errors, files = [], []
    for p in sorted(ROOT.rglob('*')):
        rel = p.relative_to(ROOT)
        if any(part in EXCLUDED for part in rel.parts):
            continue
        if p.is_symlink():
            errors.append(f'Symlink is not allowed in the release: {rel}')
            continue
        if not p.is_file():
            continue
        approved = rel.as_posix() in ROOT_FILES | REPOSITORY_FILES or p.is_relative_to(SKILL)
        if not approved or (len(rel.parts) > 1 and p.suffix not in ALLOWED_EXTENSIONS and p.name != 'LICENSE' and not is_icon(p)):
            errors.append(f'Unapproved release file: {rel}')
            continue
        if p.stat().st_size > 2_000_000:
            errors.append(f'Unexpectedly large source file: {rel}')
            continue
        files.append(p)
    return files, errors


def validate():
    files, errors = public_files()
    required = [ROOT / n for n in ROOT_FILES | REPOSITORY_FILES] + [SKILL / 'SKILL.md', SKILL / 'LICENSE', SKILL / 'NOTICE.md']
    for p in required:
        if not p.is_file():
            errors.append(f'Missing required file: {p.relative_to(ROOT)}')
    if errors:
        raise ValueError('\n'.join(errors))
    text = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
    front = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
    if not front:
        errors.append('SKILL.md must begin with YAML frontmatter')
    else:
        name = re.search(r'^name:\s*([a-z0-9-]+)\s*$', front[1], re.M)
        if not name or name[1] != SKILL.name:
            errors.append('The skill name must match the folder name')
        if not re.search(r'^description:\s*\S', front[1], re.M):
            errors.append('Missing skill description')
    if 'TODO' in text or '[TODO' in text:
        errors.append('Unfinished skill scaffold')
    version = re.search(r'^\s+version:\s*"([0-9]+\.[0-9]+\.[0-9]+)"', text, re.M)
    if not version:
        errors.append('Missing semantic version metadata')
    links = 0
    for p in files:
        if is_icon(p):
            if not p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):
                errors.append(f'Invalid icon PNG: {p.relative_to(ROOT)}')
            continue
        data = p.read_text(encoding='utf-8')
        # Generic leak checks; approved public contact details are allowed.
        if re.search(r'/(?:Users|home)/[^/\s]+/', data):
            errors.append(f'Host-specific home path: {p.relative_to(ROOT)}')
        if re.search(r'\bsk-[A-Za-z0-9]{20,}', data):
            errors.append(f'Possible credential: {p.relative_to(ROOT)}')
        if p.suffix != '.md':
            continue
        targets = re.findall(r'\]\(([^)]+)\)', data)
        targets += re.findall(r'''(?:src|href)=["']([^"']+)["']''', data)
        for target in targets:
            target = target.strip('<>')
            if urlsplit(target).scheme or target.startswith('#'):
                continue
            dest = (p.parent / unquote(target.split('#', 1)[0])).resolve()
            boundary = SKILL if p.is_relative_to(SKILL) else ROOT
            if not dest.is_relative_to(boundary):
                errors.append(f'Link escapes its package: {p.relative_to(ROOT)} -> {target}')
            elif not dest.exists():
                errors.append(f'Broken local link: {p.relative_to(ROOT)} -> {target}')
            links += 1
    for name in ('LICENSE', 'NOTICE.md'):
        if (ROOT / name).read_bytes() != (SKILL / name).read_bytes():
            errors.append(f'Standalone skill must retain the same {name}')
    interface = SKILL / 'agents' / 'openai.yaml'
    if interface.is_file():
        for target in re.findall(r'^\s+icon_(?:small|large):\s*"([^"]+)"', interface.read_text(encoding='utf-8'), re.M):
            destination = (SKILL / target).resolve()
            if not destination.is_relative_to(SKILL) or not destination.is_file():
                errors.append(f'Invalid UI icon reference: {target}')
    if errors:
        raise ValueError('\n'.join(errors))
    return files, version[1], links


def validate_release(files):
    errors = []
    markers = ('[可在此填入你的 GitHub 仓库链接]', '[你的邮箱地址]')
    for p in files:
        if p.suffix == '.md' and any(marker in p.read_text(encoding='utf-8') for marker in markers):
            errors.append(f'Unfilled public contact placeholder: {p.relative_to(ROOT)}')
    for p in (ROOT / 'README.md', SKILL / 'references' / 'plan-closing.md'):
        data = p.read_text(encoding='utf-8')
        if REPOSITORY_URL not in data or CONTACT_EMAIL not in data:
            errors.append(f'Missing confirmed repository or email: {p.relative_to(ROOT)}')
    if errors:
        raise ValueError('\n'.join(errors))


def build_archive(destination, files, base, version, kind):
    payload = {p.relative_to(base).as_posix(): p.read_bytes() for p in files}
    manifest = {'package': 'fitness-companion', 'version': version, 'kind': kind,
                'sha256': {name: sha256(data) for name, data in sorted(payload.items())}}
    # Each ZIP has one top-level folder; extracting it cannot write above that folder.
    prefix = 'fitness-companion/'
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(payload.items()):
            z.writestr(prefix + name, data)
        if kind == 'skill':
            z.writestr(prefix + 'MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    with zipfile.ZipFile(destination) as z:
        if z.testzip():
            raise ValueError('Archive integrity test failed')
        for name, digest in manifest['sha256'].items():
            if sha256(z.read(prefix + name)) != digest:
                raise ValueError(f'Archive hash mismatch: {name}')
    return {'file': destination.name, 'files': len(payload), 'bytes': destination.stat().st_size,
            'sha256': sha256(destination.read_bytes())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Validate source files without building ZIPs')
    parser.add_argument('--release', action='store_true', help='Also check confirmed public contacts and placeholders')
    parser.add_argument('--repository', action='store_true', help='Also build a clean repository archive; implies --release')
    args = parser.parse_args()
    try:
        files, version, links = validate()
        if args.release or args.repository:
            validate_release(files)
        report = {'version': version, 'source_files': len(files), 'local_links_checked': links,
                  'release_details_checked': args.release or args.repository}
        if not args.check:
            out = ROOT / 'dist'
            out.mkdir(exist_ok=True)
            products = [build_archive(out / f'fitness-companion-skill-v{version}.zip', [p for p in files if p.is_relative_to(SKILL)], SKILL, version, 'skill')]
            if args.repository:
                products.append(build_archive(out / f'fitness-companion-repository-v{version}.zip', files, ROOT, version, 'repository'))
            (out / 'SHA256SUMS.txt').write_text(''.join(f'{p["sha256"]}  {p["file"]}\n' for p in products), encoding='utf-8')
            report['archives'] = products
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (ValueError, OSError, UnicodeError) as exc:
        parser.exit(1, f'Release validation failed:\n{exc}\n')


if __name__ == '__main__':
    main()
