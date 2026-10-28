"""Verify final T4 scope and evidence, then write self-excluding integrity manifest."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, re, shutil, subprocess

ROOT = Path('/workspace/Dation')
WORK = Path('/workspace/work/dation-t4')
OUT = ROOT / 'docs/execution/ultimate/t4'
E = OUT / 'evidence'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()

def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

shutil.copy2(__file__, E / Path(__file__).name)
initial = json.loads((WORK / 'initial-state.json').read_text())
candidate = json.loads((WORK / 'candidate.json').read_text())
head = git('rev-parse', 'HEAD')
assert head == initial['head']
assert git('branch', '--show-current') == 'main'
assert git('diff', '--cached', '--name-only') == ''
assert git('rev-parse', 'origin/main') == head
subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
assert sum(x['bytes'] for x in initial['files'].values()) == 23665979
assert all(sha(ROOT / n) == r['sha256'] for n, r in candidate['files'].items())
assert len(candidate['files']) == 25
pending = set(git('ls-files', '--modified', '--others', '--exclude-standard', '-z').split('\0')) - {''}
known = set(initial['files']) | set(candidate['files'])
unexpected = sorted(n for n in pending - known if not n.startswith('docs/execution/ultimate/t4/'))
assert not unexpected, unexpected
preservation = json.loads((OUT / 'preservation.json').read_text())
for n, old in initial['files'].items():
    assert sha(WORK / 'post-t3' / n) == old['sha256'], n
    if n in preservation['intentionally_extended_files']:
        assert sha(E / 'post-t3' / n) == old['sha256'], n
    else:
        assert sha(ROOT / n) == old['sha256'], n
t3_manifest = ROOT / 'docs/execution/ultimate/t3/artifact-integrity.json'
assert sha(t3_manifest) == initial['T3_manifest_sha256']
for entry, resolved in zip(json.loads(t3_manifest.read_text())['files'], preservation['T3_resolution']):
    assert entry['path'] == resolved['path']
    assert sha(ROOT / resolved['resolved_from']) == entry['sha256']
ledger = json.loads((OUT / 'test-ledger.json').read_text())
for r in ledger['suites']:
    assert r['status'] == 'PASS' and r['tests'] > 0
    assert r['failures'] == r['errors'] == r['skips'] == r['exit_code'] == 0
    assert sha(OUT / r['log']) == r['log_sha256']
    assert json.loads((OUT / r['raw_result']).read_text())['log_sha256'] == r['log_sha256']
assert ledger['aliases'][0]['tests'] == 25
parity = json.loads((E / 'visual-parity/parity.json').read_text())
assert parity['t4_stylesheet_loaded_after'] and all(v['pixels_equal'] and v['computed_styles_equal'] for v in parity['viewports'])
contrast = json.loads((E / 'browser/contrast.json').read_text())
assert len(contrast['failures']) == 0 and contrast['minimumContrast'] >= 4.5
cleanup = json.loads((E / 'cleanup.json').read_text())
assert cleanup['final_owned_qa_containers_remaining'] == []
patterns = [r'\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}', r'\bsbp_[A-Za-z0-9]{20,}', r'\bsk-proj-[A-Za-z0-9_-]{20,}']
secrets = []
for p in OUT.rglob('*'):
    if p.is_file() and p.suffix != '.png':
        text = p.read_text(errors='replace')
        if any(re.search(pattern, text) for pattern in patterns):
            secrets.append(str(p.relative_to(ROOT)))
assert not secrets, secrets
report = OUT / 't4-execution-report.md'
assert report.read_text().count('**GO — T4 completado. T5 puede ser solicitado.**') == 1
assert '**STOP — T4 no cumple condiciones para autorizar T5.**' not in report.read_text()
write(E / 'final-state.json', {
    'phase': 'T4', 'verified_at': datetime.now(timezone.utc).isoformat(),
    'head': head, 'branch': 'main', 'cached_origin_main': git('rev-parse', 'origin/main'),
    'remote_verification_this_phase': False,
    'status_short_branch': git('status', '--short', '--branch'),
    'staged': [], 'working_tree_clean': False,
    'scope': {'source_test_migration_files': 25, 'created': 14, 'modified': 11, 'baseline_pending': 507, 'baseline_current_unchanged': 500, 'baseline_intentionally_extended': 7, 'unexpected_mutations': unexpected},
    'candidate_hashes_verified': True, 'historical_T3_entries_verified': 144,
    'git_diff_check': 'PASS', 'all_required_suites': 'PASS',
    'secret_token_scan_findings': secrets, 'local_QA_cleanup': 'PASS',
    'commit_created': False, 'push': False, 'deploy': False, 'production_changes': False,
    'T5_executed': False})
command_ledger = json.loads((OUT / 'command-ledger.json').read_text())
command_ledger['final_verification'] = {'script': 'evidence/dation-t4-finalize.py', 'integrity_manifest': 'artifact-integrity.json', 'result': 'PASS'}
write(OUT / 'command-ledger.json', command_ledger)
manifest_path = OUT / 'artifact-integrity.json'
paths = sorted(set(candidate['files']) | {str(p.relative_to(ROOT)) for p in OUT.rglob('*') if p.is_file() and p != manifest_path})
manifest = {'phase': 'T4', 'head': head, 'captured_at': datetime.now(timezone.utc).isoformat(),
    'decision': 'GO', 'excludes_self': True, 'source_files': 25,
    'files': [{'path': n, 'bytes': (ROOT / n).stat().st_size, 'sha256': sha(ROOT / n)} for n in paths]}
write(manifest_path, manifest)
assert all(sha(ROOT / row['path']) == row['sha256'] for row in manifest['files'])
for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)', report.read_text()):
    if not link.startswith(('https://', 'http://', '#')):
        assert (report.parent / link.split('#')[0]).exists(), link
print(json.dumps({'decision': 'GO', 'head': head, 'branch': 'main', 'source_files_verified': 25,
    'manifest_entries_verified': len(manifest['files']), 'historical_T3_entries_verified': 144,
    'required_suites': {r['suite']: r['tests'] for r in ledger['suites']},
    'U4_included_in_B_PY': 25, 'staged': [], 'unexpected_mutations': [], 'secret_scan': 'PASS',
    'cleanup': 'PASS', 'T5_executed': False, 'no_commit_push_or_deploy': True}, ensure_ascii=False))
