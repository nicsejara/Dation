#!/usr/bin/env python3
"""Independent, fail-closed UX release scope. Pure Git/files, no cloud access."""
import ast
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / 'infra/zero-idle/ux-autopilot-policy.json'
POLICY = json.loads(POLICY_PATH.read_text())
SHA = re.compile(r'[0-9a-f]{40}\Z')
_spec = importlib.util.spec_from_file_location('rapid_impact', ROOT / 'scripts/ci/impact.py')
impact = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(impact)


def require(ok, message):
    if not ok: raise RuntimeError('NO_GO: ' + message)


def git(*args):
    result = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True)
    require(result.returncode == 0, 'unverifiable Git evidence')
    return result.stdout.strip()


def policy_hash(): return hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest()


def allowed_runtime(path):
    return path in POLICY['runtime_paths'] or any(path.startswith(p) for p in POLICY['asset_prefixes']) and path.endswith(('.png', '.webp', '.jpg', '.jpeg'))


def image_path(path):
    return path in ('Dockerfile', '.dockerignore') or path.startswith(('backend/app/', 'sample_data/')) or path.startswith('backend/') and (path.endswith('.py') and path.count('/') == 1 or path.startswith('backend/requirements'))


def classify(paths):
    paths = sorted(set(paths))
    require(paths and any(allowed_runtime(p) for p in paths), 'no eligible product change')
    require(all(allowed_runtime(p) or p in POLICY['test_paths'] for p in paths), 'sensitive, unknown, mixed or non-UX path')
    result = impact.classify_files(paths)
    require(result['risk'] in ('R1', 'R2') and not result['requires_full'], 'only established R1/R2 risks are eligible')
    return result


def changed(base, head):
    require(SHA.fullmatch(base or '') and SHA.fullmatch(head or ''), 'full immutable Git SHAs required')
    # Renames/deletions and submodules/symlinks are not an automatic UX update.
    raw = git('diff', '--name-status', '--no-renames', base, head, '--')
    paths = []
    for line in raw.splitlines():
        status, path = line.split('\t')
        require(status in ('A', 'M') and '\n' not in path and '\t' not in path, 'delete/rename/ambiguous path requires review')
        mode = git('ls-tree', head, '--', path).split()[0]
        require(mode == '100644', 'non-regular executable/symlink/submodule denied')
        paths.append(path)
    return paths


def assertions(source):
    tree = ast.parse(source)
    # Label/selector updates preserve assertion structure, not the assertion text.
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str): node.value = '<string>'
    return Counter(ast.dump(n, include_attributes=False) for n in ast.walk(tree) if isinstance(n, ast.Assert) or isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and (n.func.attr.startswith('assert') or n.func.attr.startswith('to_')))


def validate_test_changes(base, head, paths):
    for path in paths:
        if path not in POLICY['test_paths']: continue
        old = git('show', base + ':' + path)
        new = git('show', head + ':' + path)
        require(not (assertions(old) - assertions(new)), 'existing browser assertions removed or weakened structurally')
        require(not re.search(r'@(?:unittest\.)?skip|\bskipTest\s*\(', new), 'test skipping is forbidden')


def client_interfaces(text):
    # Fail closed on network/API/import/auth surface changes in otherwise allowed UI files.
    import_rx = r"(?:from\s*|import\s*\(\s*|@import\s*)['\"]([^'\"]+)['\"]"
    routes_rx = r"['\"](/api/[^'\"]*)['\"]"
    verbs_rx = r"['\"](GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)['\"]"
    sensitive_rx = r"\b(?:fetch|XMLHttpRequest|eval|sendBeacon|localStorage|sessionStorage)\b|document\.cookie|https?://[^\s'\")]+"
    return [Counter(re.findall(pattern, text)) for pattern in (import_rx,routes_rx,verbs_rx,sensitive_rx)]


def validate_client_changes(base, head, paths):
    for path in paths:
        if allowed_runtime(path) and path.endswith(('.mjs','.css')):
            old = git('show', base + ':' + path)
            new = git('show', head + ':' + path)
            require(client_interfaces(old)==client_interfaces(new),'UI import/API/auth/network surface changed; explicit review required')


def eligible_commit(sha, pull, baseline):
    require(SHA.fullmatch(sha or '') and SHA.fullmatch(baseline or ''), 'invalid candidate/baseline')
    require(pull.get('merged') is True and pull.get('merge_commit_sha') == sha and pull.get('base', {}).get('ref') == 'main', 'not a verified merged main PR')
    require(pull.get('base', {}).get('repo', {}).get('id') == POLICY['repository_id'] and pull.get('head', {}).get('repo', {}).get('id') == POLICY['repository_id'], 'fork or wrong repository')
    require(pull.get('user', {}).get('id') == POLICY['owner_id'] and pull.get('merged_by', {}).get('id') == POLICY['owner_id'], 'only owner-authorized same-repository PRs')
    parents = git('show', '-s', '--format=%P', sha).split()
    require(len(parents) in (1, 2), 'octopus/root commit denied')
    first = parents[0]
    paths = changed(first, sha)
    result = classify(paths)
    validate_test_changes(first, sha, paths)
    validate_client_changes(first, sha, paths)
    if len(parents) == 2:
        require(parents[1] == pull['head']['sha'], 'merge second parent is not PR head')
        merge_base = git('merge-base', first, parents[1])
        branch_paths = changed(merge_base, parents[1])
        classify(branch_paths); validate_test_changes(merge_base, parents[1], branch_paths)
        validate_client_changes(merge_base, parents[1], branch_paths)
    # Cumulative build-context scope closes R3->R1 and overlapping-merge laundering.
    git('merge-base', '--is-ancestor', baseline, sha)
    cumulative = [p for p in changed(baseline, sha) if image_path(p)]
    require(cumulative and all(allowed_runtime(p) for p in cumulative), 'unreleased runtime delta includes unauthorized backend/dependency/data changes')
    validate_client_changes(baseline,sha,cumulative)
    result.update(first_parent=first, baseline_sha=baseline, cumulative_image_paths=cumulative,
        pr_number=pull['number'], policy_sha256=policy_hash())
    return result
