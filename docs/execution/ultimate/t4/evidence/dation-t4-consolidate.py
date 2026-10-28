"""Consolidate completed T4 evidence; preserve T0-T3; no git mutations."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, shutil, subprocess

ROOT = Path('/workspace/Dation')
WORK = Path('/workspace/work/dation-t4')
OUT = ROOT / 'docs/execution/ultimate/t4'
E = OUT / 'evidence'
E.mkdir(parents=True, exist_ok=True)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

initial = json.loads((WORK / 'initial-state.json').read_text())
candidate = json.loads((WORK / 'candidate.json').read_text())
assert len(candidate['files']) == 25
assert all(sha(ROOT / n) == r['sha256'] for n, r in candidate['files'].items())
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip() == initial['head']
assert subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=ROOT) == b''
names = ['B-PY', 'B-NODE', 'S4', 'W4', 'FOCAL-LEGACY-API', 'FOCAL-T3-BROWSER']
results = [json.loads((WORK / (n + '.result.json')).read_text()) for n in names]
assert [r['tests'] for r in results] == [498, 134, 30, 8, 4, 1]
assert all(r['status'] == 'PASS' and r['exit_code'] == 0 and r['failures'] == r['errors'] == r['skips'] == 0 for r in results)
for n, r in zip(names, results):
    assert sha(WORK / (n + '.log')) == r['log_sha256']
    for ext in ['.log', '.result.json']:
        copy(WORK / (n + ext), E / (n + ext))

for n in ['T4-user-request.txt', 'initial-state.json', 'post-t3-tracked.patch', 'candidate.json', 'candidate-before-copy.json', 'candidate-before-composition-fix.json', 't4-changes.patch', 'qa-reuse.json', 'qa-reuse-before-composition-fix.json', 'qa-batch.log', 'qa-final-w4.log', 'qa-final-composition.log', 'schema-boundary.json', 'cleanup.json', 'evidence-label-corrections.json']:
    copy(WORK / n, E / n)
for folder in ['attempts', 'visual-before', 'visual-parity', 'browser', 'legacy-api', 'samples']:
    shutil.copytree(WORK / folder, E / folder, dirs_exist_ok=True)
for width in [1440, 390]:
    copy(WORK / 'browser-before-composition-fix' / f'case-data-{width}.png', E / 'visual-composition-fix' / f'before-{width}.png')
for n in ['dation-t4-qa.py', 'dation-t4-before-visual.py', 'dation-t4-schema-evidence.py', 'dation-t4-visual-parity.py', 'dation-t4-consolidate.py']:
    copy(Path('/tmp') / n, E / n)

unchanged, changed = [], []
for name, old in initial['files'].items():
    assert sha(WORK / 'post-t3' / name) == old['sha256'], name
    if sha(ROOT / name) == old['sha256']:
        unchanged.append(name)
    else:
        assert name in candidate['files'], name
        copy(WORK / 'post-t3' / name, E / 'post-t3' / name)
        changed.append(name)
assert len(unchanged) == 500 and len(changed) == 7
manifest_path = ROOT / 'docs/execution/ultimate/t3/artifact-integrity.json'
manifest = json.loads(manifest_path.read_text())
assert sha(manifest_path) == initial['T3_manifest_sha256']
resolution = []
for entry in manifest['files']:
    name = entry['path']
    p = E / 'post-t3' / name if name in changed else ROOT / name
    assert sha(p) == entry['sha256'], name
    resolution.append({'path': name, 'matches_historical_hash': True, 'resolved_from': str(p.relative_to(ROOT))})
assert len(resolution) == 144
write(OUT / 'preservation.json', {
    'phase': 'T4', 'baseline_pending_files': len(initial['files']),
    'checkpoint_copies_verified': len(initial['files']), 'unchanged_current_files': len(unchanged),
    'intentionally_extended_files': changed, 'preimages': 'evidence/post-t3/',
    'historical_T3_manifest_unchanged': True, 'historical_T3_entries_verified': len(resolution),
    'T3_resolution': resolution, 'old_reports_migrations_contracts_tests_preserved': True,
    'candidate_verified': True, 'source_files': len(candidate['files'])})
created = [n for n, r in candidate['files'].items() if r['baseline'] == 'new T4 file']
modified = [n for n, r in candidate['files'].items() if r['baseline'] != 'new T4 file']
assert len(created) == 14 and len(modified) == 11
write(OUT / 'scope-diff.json', {'phase': 'T4', 'baseline': initial['head'], 'files': candidate['files'],
    'created': created, 'modified': modified, 'comparison': 'Immediate post-T3 checkpoint; HEAD only for previously clean files',
    'no_infrastructure_or_global_design_token_changes': True})

u4_lines = [line for line in (WORK / 'B-PY.log').read_text().splitlines() if '(test_ultimate_data_contracts.' in line and line.endswith(' ... ok')]
assert len(u4_lines) == 25
for r in results:
    r.update(log='evidence/' + r['suite'] + '.log', raw_result='evidence/' + r['suite'] + '.result.json')
write(OUT / 'test-ledger.json', {'phase': 'T4', 'suites': results,
    'aliases': [{'suite': 'U4', 'status': 'PASS', 'tests': 25, 'included_in': 'B-PY',
        'module': 'tests.test_ultimate_data_contracts', 'log_lines': u4_lines, 'repeated_only_for_alias': False}],
    'additional_boundaries': [
        {'name': 'schema-boundary', 'status': 'PASS', 'evidence': 'evidence/schema-boundary.json'},
        {'name': 'native-visual-parity', 'status': 'PASS', 'viewports': [1440, 1280, 1024, 768, 390], 'evidence': 'evidence/visual-parity/parity.json'},
        {'name': 'responsive-stress', 'status': 'PASS', 'viewports': [1440, 1280, 1024, 768, 390, 320], 'zoom': '200%', 'evidence': 'evidence/browser/responsive.json'},
        {'name': 'keyboard-focus', 'status': 'PASS', 'evidence': 'evidence/browser/keyboard-focus.json'},
        {'name': 'contrast', 'status': 'PASS', 'evidence': 'evidence/browser/contrast.json'}],
    'not_run': [
        {'suite': 'B-BROWSER full', 'reason': 'W4 plus affected legacy upload browser test and one T3 setup browser focal'},
        {'suite': 'B-E2E full', 'reason': 'Four affected legacy Hub/upload/recovery/history tests plus S4'},
        {'suite': 'B-SQL historical full', 'reason': 'S4 full-catalog RPC/API suite plus schema/ACL/RLS/legacy-row boundary'}],
    'inherited_baseline': {'T3': 'docs/execution/ultimate/t3/t3-execution-report.md', 'B-PY': 473, 'B-NODE': 132, 'S3': 25, 'W3': 9},
    'qa_reuse': ['evidence/qa-reuse.json'], 'all_suites_match_final_affected_source_files': True,
    'latest_UI_composition_change_consumers_repeated': ['W4', 'native-visual-parity'], 'no_solver_or_LLM_required': True})

skills = []
applied = {
    'design-system': ('Read main and states guide in T4; reused native tokens, cards, drop-card factory, dialog and drawer. No generator.', 'Native pixels/computed styles identical at five widths; scoped CSS only.'),
    'emil-design-eng': ('Guidance read earlier in this conversation; applied native focus/Escape/return, immediate validation, reduced motion; no new animation.', 'W4 keyboard, modal, drawer, reduced motion and Before/After/Why table.'),
    'ui-ux-pro-max': ('Reused focused form/accessibility guidance read in T3; exact headers from server and native error states.', 'W4 guided invalid schema/preview, responsive/contrast; no palette/font generation.'),
    'break-ui': ('Guidance and catalog read earlier in this conversation; schema-backed filename length120, Unicode, empty/one/multiple states, 320px/zoom200%.', 'W4 stress/touch and preserved screenshots, fixture-only data.')}
for name, (action, verified) in applied.items():
    src = ROOT / '.agents/skills' / name / 'SKILL.md'
    copy(src, E / 'skills' / name / 'SKILL.md')
    skills.append({'name': name, 'source': str(src.relative_to(ROOT)), 'sha256': sha(src), 'read': True,
        'applied': action, 'verified': verified, 'source_snapshot': 'evidence/skills/' + name + '/SKILL.md'})
for name, package, snapshot, action, verified in [
    ('supabase:supabase', 'c0/supabase', 'supabase-skill.txt', 'Checked service-role RPC, membership/DDA/actor/tenant checks, private Storage with immutable objects, additional default-closed flag.', 'S4 30, Storage fault injection, schema ACL/RLS preservation; official Storage documentation consulted.'),
    ('supabase:supabase-postgres-best-practices', 'c0/supabase-postgres-best-practices', 'postgres-skill.txt', 'Ordered workspace-to-Case locks, CAS, complete manifest transaction, uniqueness/FKs and immutable metadata.', 'S4 concurrency, stale revision/replay, cross-tenant and consumed-delete negatives.'),
    ('cloud-environment:cloud-environment-runtime', 'c5/cloud-environment-runtime', 'runtime-skill.txt', 'Environment status/network policy, owned labelled local SQL fixture, credential-cleared Python/Chromium, local Docker socket.', 'Version checks, no productive access/writes, scoped resource cleanup evidence.')]:
    src = WORK / 'skills' / snapshot
    copy(src, E / 'skills' / snapshot)
    skills.append({'name': name, 'package': package, 'source_snapshot': 'evidence/skills/' + snapshot,
        'sha256': sha(src), 'read': True, 'read_during_T4': True, 'applied': action, 'verified': verified})
references = [
    ('design-system/references/states-and-variants.md', 'read during T4'),
    ('design-system/references/token-architecture.md', 'reused same-conversation reading'),
    ('break-ui/CATALOG.md', 'reused same-conversation reading'),
    ('postgres/schema-foreign-key-indexes.md', 'reused same-conversation reading'),
    ('postgres/security-rls-performance.md', 'reused same-conversation reading'),
    ('runtime/references/docker.md', 'read during T4'),
    ('runtime/references/networking.md', 'read during T4')]
for name in ['design-system/references/states-and-variants.md', 'design-system/references/token-architecture.md', 'break-ui/CATALOG.md']:
    copy(ROOT / '.agents/skills' / name, E / 'skills' / name)
write(OUT / 'skills-ledger.json', {'phase': 'T4', 'skills': skills,
    'references': [{'source': n, 'reading': reading} for n, reading in references],
    'omitted': [
        {'guidance': 'New palette/fonts/starter/framework or generated design system', 'reason': 'Frozen F01/F23 and explicit native UI preservation.'},
        {'guidance': 'break-ui stop before implementing any finding', 'reason': 'Explicit end-to-end T4 authorization takes precedence for scoped fixes.'},
        {'guidance': 'General audit, improve-animations, automatic review-animations', 'reason': 'No transversal audit authorized; no new animation; review-animations requires explicit invocation.'},
        {'guidance': 'Production migration or bucket configuration', 'reason': 'User explicitly prohibits productive Storage, migrations, deployment and push.'}],
    'unavailable_required_dependencies': [], 'application_dependencies_added': False, 'UI_preservation_gate': 'PASS'})
write(OUT / 'command-ledger.json', {'phase': 'T4',
    'suites': [{k: r[k] for k in ['suite', 'cwd', 'command', 'PYTHONPATH', 'started_at', 'finished_at', 'seconds', 'exit_code']} for r in results],
    'driver': 'evidence/dation-t4-qa.py',
    'additional_commands': [
        {'command': ['/workspace/Dation/.venv/bin/python', '-B', '/tmp/dation-t4-schema-evidence.py'], 'evidence': 'evidence/attempts/schema-boundary.log'},
        {'command': ['/workspace/Dation/backend/.browser-venv/bin/python', '-B', '/tmp/dation-t4-visual-parity.py'], 'evidence': 'evidence/attempts/visual-parity.log'},
        {'command': ['/workspace/Dation/backend/.browser-venv/bin/python', '-B', '/tmp/dation-t4-before-visual.py'], 'evidence': 'evidence/visual-before/'},
        {'command': ['git', 'diff', '--check'], 'result': 'PASS'}],
    'U4_alias': '25 tests executed inside B-PY, not repeated for naming alone.',
    'production_credentials_cleared': ['SUPABASE_URL', 'SUPABASE_SECRET_KEY', 'SUPABASE_ACCESS_TOKEN', 'LLM_API_KEY', 'LLM_BASE_URL', 'GCP_ACCESS_TOKEN'],
    'docker_transport': 'local Unix socket; inherited Docker transport override variables removed for local fixture only',
    'documentation_network': 'Official Supabase MCP documentation search; CLI changelog request rejected by proxy403, not bypassed.',
    'no_remote_writes': True, 'no_commit_push_or_deploy': True})
write(E / 'runtime.json', {'date': '2026-10-26', 'client_timezone': 'America/Buenos_Aires',
    'python': '3.13.5', 'node': '24.19.0', 'chromium': '151.0.7922.173', 'docker': '28.4.0',
    'postgres': '17.11', 'supabase_cli': '2.122.0',
    'application_python': '/workspace/Dation/.venv/bin/python', 'browser_python': '/workspace/Dation/backend/.browser-venv/bin/python',
    'docker_socket': 'unix:///var/run/docker.sock', 'SQL_container': 'dation-t4-20261026-inputs',
    'SQL_labels': {'dation.qa.phase': 'T4', 'dation.qa.owner': 'codex-dation'},
    'network': 'Restricted session proxy; local fixtures; no VPN; no allowlist bypass.',
    'production_credentials_used': False, 'application_dependencies_added': False})
print(json.dumps({'T4_source_files': len(candidate['files']), 'created': len(created), 'modified': len(modified),
    'baseline_unchanged': len(unchanged), 'baseline_extended': changed, 'T3_entries_verified': len(resolution),
    'required_suites': 'PASS', 'evidence_dir': str(E)}, ensure_ascii=False))
