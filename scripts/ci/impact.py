#!/usr/bin/env python3
"""Fail-closed, reviewable CI impact classifier. No cloud credentials or network."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RISK = {'R0': 0, 'R1': 1, 'R2': 2, 'R3': 3, 'R4': 4}
MAP = json.loads((ROOT / 'tests/impact-map.json').read_text())

def classify_files(paths):
    paths = sorted({str(p) for p in paths if str(p).strip()})
    if not paths:
        return {'risk': 'R4', 'reason': 'No verified diff; fail closed', 'files': [], 'browser_tests': [], 'requires_full': True}
    risk, why, suites = 'R0', [], set()
    for path in paths:
        if path.startswith(('.github/', 'infra/', 'scripts/runtime_v2_publication.py', 'scripts/release/')) or path in ('Dockerfile', '.dockerignore', 'backend/requirements.txt', 'backend/requirements-browser.txt'):
            kind = 'R4'
        elif path.startswith(('backend/app/static/js/', 'backend/app/templates/', 'backend/tests/browser/')) or path.startswith('backend/app/static/css/ultimate-'):
            kind = 'R2'
        elif path.startswith('backend/app/static/css/') or path.startswith('backend/app/static/img/'):
            kind = 'R1'
        elif path.startswith(('docs/', 'README', 'LICENSE')) or (path.endswith('.md') and not path.startswith(('scripts/', '.github/'))):
            kind = 'R0'
        else:
            kind = 'R3'  # Unknown, backend, migrations, tests and policies are never downgraded.
        if RISK[kind] > RISK[risk]:
            risk = kind
        why.append(f'{kind}:{path}')
        if kind == 'R2':
            matches = []
            for entry in MAP['browser_suites']:
                if any(path.startswith(prefix) for prefix in entry['paths']):
                    matches.extend(entry['tests'])
            suites.update(matches or MAP['default_browser_tests'])
    return {'risk': risk, 'reason': '; '.join(why), 'files': paths,
            'browser_tests': sorted(suites) if risk == 'R2' else [],
            'requires_full': RISK[risk] >= RISK['R3']}

def diff_paths(base, head):
    if not re.fullmatch(r'[0-9a-f]{40}', base or '') or not re.fullmatch(r'[0-9a-f]{40}', head or ''):
        raise ValueError('Unverified base or head commit SHA')
    completed = subprocess.run(['git', 'diff', '--name-only', '-z', '--no-ext-diff', base, head, '--'],
                               cwd=ROOT, capture_output=True, check=True)
    return [p for p in completed.stdout.decode().split('\0') if p]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--github-output')
    opts = parser.parse_args()
    try:
        result = classify_files(diff_paths(opts.base, opts.head))
    except (ValueError, subprocess.CalledProcessError, UnicodeError) as exc:
        result = classify_files([])
        result['reason'] = f'Unverifiable diff ({type(exc).__name__}); fail closed'
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if opts.github_output:
        output = Path(opts.github_output)
        with output.open('a') as handle:
            for key, val in {'risk': result['risk'],
                             'requires_full': str(result['requires_full']).lower(),
                             'browser_tests': json.dumps(result['browser_tests'])}.items():
                handle.write(f'{key}={val}\n')

if __name__ == '__main__':
    main()
