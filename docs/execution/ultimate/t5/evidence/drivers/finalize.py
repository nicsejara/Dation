"""Verify T5 receipts and record the final local state; no git mutations."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import shutil
import subprocess

R = Path('/workspace/Dation')
W = Path('/workspace/work/dation-t5')
O = R / 'docs/execution/ultimate/t5'
E = O / 'evidence'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(p):
    return json.loads(p.read_text())

def write(p, value):
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def git(*args):
    return subprocess.check_output(['git', *args], cwd=R)

initial = read(E / 'initial-state.json')
candidate = read(E / 'candidate.json')
preserved = read(O / 'preservation.json')
ledger = read(O / 'test-ledger.json')
head = git('rev-parse', 'HEAD').decode().strip()
branch = git('branch', '--show-current').decode().strip()
assert head == initial['head'] == candidate['head'] == 'ef997235a30251fbf7ae53690ed738092ee973d8'
assert branch == 'main'
assert git('rev-parse', 'origin/main').decode().strip() == head
assert not git('diff', '--cached', '--name-only')
subprocess.run(['git', 'diff', '--check'], cwd=R, check=True)
assert len(candidate['files']) == 29
for name, entry in candidate['files'].items():
    assert sha(R / name) == entry['sha256'], name
    assert (R / name).stat().st_size == entry['bytes'], name

unchanged = 0
extended = []
assert len(initial['files']) == 627
for name, entry in initial['files'].items():
    assert sha(W / 'post-t4' / name) == entry['sha256'], name
    assert (R / name).exists(), name
    if sha(R / name) == entry['sha256']:
        unchanged += 1
    else:
        assert name in candidate['files'], name
        assert sha(E / 'post-t4' / name) == entry['sha256'], name
        extended.append(name)
assert unchanged == 618 and len(extended) == 9
assert sorted(extended) == sorted(preserved['intentionally_extended_baseline_files'])
t4manifest = R / 'docs/execution/ultimate/t4/artifact-integrity.json'
assert sha(t4manifest) == initial['T4_manifest_sha256']
assert len(preserved['T4_resolution']) == 147
for entry, receipt in zip(read(t4manifest)['files'], preserved['T4_resolution']):
    assert entry['path'] == receipt['path']
    assert sha(R / receipt['resolved_from']) == entry['sha256'], entry['path']
recovery = read(E / 'recovery-verification.json')
for name, entry in recovery['pre_stop_T5_files'].items():
    assert sha(E / 'pre-stop' / name) == entry['sha256'], name
assert len(preserved['pre_STOP_files_unchanged']) == 6
for name in preserved['pre_STOP_files_unchanged']:
    assert sha(R / name) == recovery['pre_stop_T5_files'][name]['sha256'], name

expected = {'B-PY': 521, 'B-NODE': 137, 'S5': 19, 'W5': 10, 'B-FOCUS': 9, 'FOCAL-CASE-CREATE': 1}
assert {s['suite']: s['tests'] for s in ledger['suites']} == expected
for suite in ledger['suites']:
    assert suite['status'] == 'PASS'
    assert suite['failures'] == suite['errors'] == suite['skips'] == suite['exit_code'] == 0
    assert sha(O / suite['log']) == suite['log_sha256']
    result = read(O / suite['raw_result'])
    assert all(result[k] == suite[k] for k in ['suite', 'tests', 'status', 'failures', 'errors', 'skips', 'exit_code', 'log_sha256'])
assert ledger['aliases'][0]['suite'] == 'U5'
assert ledger['aliases'][0]['tests'] == len(ledger['aliases'][0]['log_lines']) == 23
assert sha(O / ledger['pre_STOP_U5']['log']) == ledger['pre_STOP_U5']['log_sha256']
schema = read(E / 'schema-boundary.json')
for flag in ['legacy_rows_unchanged', 'prior_definition_snapshots_unchanged', 'no_new_node_state_table', 'columns_constraints_indexes_policies_relations_triggers_defaults_unchanged', 'existing_functions_and_ACLs_unchanged']:
    assert schema[flag] is True, flag
for name in ['visual-parity', 'legacy-map-parity']:
    parity = read(E / name / 'parity.json')
    assert all(v['pixels_equal'] for v in parity['viewports'])
cleanup = read(E / 'cleanup.json')
assert cleanup['remaining_owned_T5_containers'] == []
assert cleanup['production_resources_modified'] is False

# Inspect only new T5 evidence for accidentally retained credentials. Values are
# never printed; fixture source code and intentionally fake examples are not secrets.
patterns = {
    'JWT': re.compile(rb'\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}'),
    'Supabase personal token': re.compile(rb'\bsbp_[A-Za-z0-9]{30,}'),
    'OpenAI project token': re.compile(rb'\bsk-proj-[A-Za-z0-9_-]{30,}'),
}
findings = []
for p in O.rglob('*'):
    if not p.is_file() or p.suffix.lower() == '.png':
        continue
    data = p.read_bytes()
    for kind, pattern in patterns.items():
        if pattern.search(data):
            findings.append({'path': str(p.relative_to(R)), 'kind': kind})
assert not findings, findings

shutil.copy2(Path(__file__), E / 'drivers/finalize.py')
commands = read(O / 'command-ledger.json')
commands['final_integrity_verification'] = {
    'script': 'evidence/drivers/finalize.py',
    'checks': ['frozen source hashes', 'checkpoint and T4 receipts', 'suite log hashes', 'scope', 'git diff --check', 'report links', 'artifact hashes'],
    'no_new_test_suite_execution': True,
}
write(O / 'command-ledger.json', commands)

manifest_path = O / 'artifact-integrity.json'
if not manifest_path.exists():
    write(manifest_path, {'phase': 'T5', 'finalizing': True})
final_state = E / 'final-state.json'
if not final_state.exists():
    write(final_state, {'phase': 'T5', 'finalizing': True})

status_raw = git('status', '--porcelain=v1', '-z', '--untracked-files=all').decode()
status_paths = []
for record in status_raw.split('\0'):
    if record:
        assert record[:2] not in ['R ', 'C '], record[:2]
        status_paths.append(record[3:])
allowed = set(initial['files']) | set(candidate['files'])
unexpected = [p for p in status_paths if p not in allowed and not p.startswith('docs/execution/ultimate/t5/')]
assert not unexpected, unexpected
status = git('status', '--short', '--branch', '--untracked-files=all').decode()
write(final_state, {
    'phase': 'T5', 'captured_at': datetime.now(timezone.utc).isoformat(),
    'HEAD': head, 'branch': branch, 'origin_main_cached': head,
    'remote_reference_fetched': False, 'staged_paths': [],
    'working_tree_clean': False, 'pending_paths_in_git_status': len(status_paths),
    'git_status_short_branch': status, 'git_diff_check': 'PASS',
    'frozen_T5_source_files': 29, 'created': 15, 'modified': 14,
    'baseline_pending_files': 627, 'baseline_unchanged': unchanged,
    'baseline_intentionally_extended': len(extended), 'T4_entries_verified': 147,
    'pre_STOP_partial_files_preserved': 8,
    'required_suites': expected, 'required_suites_result': 'PASS',
    'U5_tests_included_in_B_PY': 23, 'out_of_scope_pending_paths_added': [],
    'T5_evidence_credential_scan_findings': [],
    'T6_executed': False, 'commit_created': False, 'push_executed': False,
    'deploy_executed': False, 'production_modified': False,
})

files = set(candidate['files'])
files.update(str(p.relative_to(R)) for p in O.rglob('*') if p.is_file() and p != manifest_path)
entries = [{'path': name, 'bytes': (R / name).stat().st_size, 'sha256': sha(R / name)} for name in sorted(files)]
write(manifest_path, {
    'phase': 'T5', 'head': head, 'captured_at': datetime.now(timezone.utc).isoformat(),
    'decision': 'GO', 'excludes_self': True, 'source_files': 29, 'files': entries,
})
for entry in read(manifest_path)['files']:
    assert sha(R / entry['path']) == entry['sha256'], entry['path']
report = O / 't5-execution-report.md'
broken_links = []
for target in re.findall(r'\]\(([^)]+)\)', report.read_text()):
    if '://' in target or target.startswith('#'):
        continue
    path = target.split('#')[0]
    if not (report.parent / path).resolve().exists():
        broken_links.append(target)
assert not broken_links, broken_links
assert report.read_text().count('**GO — T5 completado. T6 puede ser solicitado.**') == 1
print(json.dumps({
    'result': 'PASS', 'HEAD': head, 'branch': branch,
    'source_hashes_verified': 29, 'T4_manifest_entries_verified': 147,
    'artifact_manifest_entries': len(entries), 'out_of_scope_paths': [],
    'staged_paths': [], 'git_diff_check': 'PASS', 'report_links': 'PASS',
    'required_suites': 'PASS', 'T6_executed': False,
}, ensure_ascii=False))
