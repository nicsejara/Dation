"""Manual GitHub Actions Gate C only. No deploy, Cloud Build, SQL or IAM writes."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.cloud_identity import PROJECT, PROJECT_NUMBER, REGION

TRUST = json.loads((ROOT / 'infra/zero-idle/github-publication.json').read_text())
SOURCE_SHA = os.environ.get('DATION_APPLICATION_SHA','')
HOST = REGION + '-docker.pkg.dev'
REPOSITORY = f'projects/{PROJECT}/locations/{REGION}/repositories/dation-runtime'
PACKAGE = REPOSITORY + '/packages/dation-core'
IMAGE = f'{HOST}/{PROJECT}/dation-runtime/dation-core'
TAG = IMAGE + ':' + SOURCE_SHA
PROVIDER = f'projects/{PROJECT_NUMBER}/locations/global/workloadIdentityPools/dation-github-publish/providers/github-main-manual'
ACCOUNT = f'dation-image-builder@{PROJECT}.iam.gserviceaccount.com'
CRANE_ARCHIVE_SHA = '0ab7a1d6932a213aed964ce97666c3077fe691c8606413674a8b3e0b9ec4cda0'
CRANE_SHA = '8e75c326adb43b053cfd78b9b987663f8f4fe4557f4d3915905643f25c730992'
CRANE_URL = 'https://github.com/google/go-containerregistry/releases/download/v0.22.1/go-containerregistry_Linux_x86_64.tar.gz'
PERMISSIONS = {'artifactregistry.repositories.uploadArtifacts', 'artifactregistry.repositories.downloadArtifacts',
               'artifactregistry.tags.get', 'artifactregistry.tags.create', 'artifactregistry.versions.list'}


def wif_plan():
    claims = {'repository': TRUST['repository'], 'repository_id': TRUST['repository_id'],
        'repository_owner_id': TRUST['repository_owner_id'], 'ref': TRUST['ref'],
        'event_name': TRUST['event'], 'workflow_ref': TRUST['workflow_ref'],
        'sub': 'repo:nicsejara/Dation:ref:refs/heads/main'}
    return {'project': PROJECT, 'project_number': PROJECT_NUMBER, 'region': REGION,
        'pool_id': TRUST['pool_id'], 'provider_id': TRUST['provider_id'], 'provider': PROVIDER,
        'issuer': 'https://token.actions.githubusercontent.com', 'audience': 'https://iam.googleapis.com/' + PROVIDER,
        'attribute_mapping': {'google.subject': 'assertion.repository_id'},
        'attribute_condition': ' && '.join('assertion.' + key + " == '" + value + "'" for key, value in claims.items()),
        'expected_claims': claims, 'service_account': ACCOUNT,
        'principal': f'principal://iam.googleapis.com/projects/{PROJECT_NUMBER}/locations/global/workloadIdentityPools/dation-github-publish/subject/1114679650',
        'repository_resource': REPOSITORY, 'required_apis': ['iam.googleapis.com', 'iamcredentials.googleapis.com', 'sts.googleapis.com'],
        'obsolete_source_bucket': 'dation-runtime-v2-2026-build-src-usw1-332279365872'}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def digest_file(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def outputs(**values):
    with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
        for key, value in values.items():
            require('\n' not in str(value), 'Invalid multiline action output')
            stream.write(f'{key}={value}\n')


def guard_context(env=os.environ):
    require(TRUST['application_sha_source'] == 'workflow_dispatch.application_sha',
        'Expected workflow-dispatch SHA input')
    require(bool(re.fullmatch(r'[0-9a-f]{40}', SOURCE_SHA)) and env.get('DATION_APPLICATION_SHA') == SOURCE_SHA,
        'Missing or invalid exact application SHA')
    expected = {'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY': 'nicsejara/Dation',
        'GITHUB_REPOSITORY_ID': '1114679650', 'GITHUB_REPOSITORY_OWNER_ID': '249153366',
        'GITHUB_REF': 'refs/heads/main', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
        'GITHUB_WORKFLOW_REF': 'nicsejara/Dation/.github/workflows/runtime-v2-publish.yml@refs/heads/main',
        'GITHUB_RUN_ATTEMPT': '1'}
    require(all(env.get(k) == v for k, v in expected.items()), 'Only first-attempt manual publication from the trusted main workflow is allowed')
    require(re.fullmatch(r'[0-9]+', env.get('GITHUB_RUN_ID', '')), 'Missing Actions run identity')


def command(*args, timeout=120, secret_input=None):
    try:
        result = subprocess.run(list(map(str, args)), input=secret_input, text=True,
            capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(Path(str(args[0])).name + ' timed out; no automatic build retry') from None
    if result.returncode and secret_input is None:
        diagnostic = (result.stdout + result.stderr)[-12000:]
        for key in ('DATION_PUBLISH_ACCESS_TOKEN', 'GH_TOKEN', 'ACTIONS_RUNTIME_TOKEN'):
            value = os.environ.get(key)
            if value:
                diagnostic = diagnostic.replace(value, '[REDACTED]')
        diagnostic = re.sub(r'(?i)Authorization:\s*(?:Bearer|Basic)\s+\S+', 'Authorization: [REDACTED]', diagnostic)
        print(diagnostic, file=sys.stderr)
    require(result.returncode == 0, Path(str(args[0])).name + ' failed; no automatic build retry')
    return result.stdout.strip()


def source_check(source, output):
    source = source.resolve(); output = output.resolve()
    require(source != output and source not in output.parents, 'Publication state must stay outside Docker context')
    auth = Path(os.environ['DOCKER_CONFIG']).resolve()
    require(source != auth and source not in auth.parents, 'Registry credentials must stay outside Docker context')
    require(command('git', '-C', source, 'rev-parse', 'HEAD') == SOURCE_SHA and
        not command('git', '-C', source, 'status', '--porcelain'), 'Exact clean validated source required')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api(method, url, body=None, absent=False, conflict=False, github=False):
    origin = 'https://api.github.com/repos/nicsejara/Dation/' if github else 'https://artifactregistry.googleapis.com/v1/' + REPOSITORY
    allowed = url.startswith(origin) if github else url == origin or url.startswith(origin + '/') or url.startswith(origin + ':')
    require(allowed, 'Unexpected API destination')
    token = os.environ['GH_TOKEN' if github else 'DATION_PUBLISH_ACCESS_TOKEN']
    headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/json', 'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(), headers=headers, method=method)
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as response:
            value = json.load(response)
            require(isinstance(value, dict), 'Ambiguous API response')
            return value
    except urllib.error.HTTPError as error:
        try:
            detail = json.loads(error.read(65536)).get('error', {})
        except (ValueError, AttributeError):
            detail = {}
        if absent and error.code == 404 and isinstance(detail, dict) and detail.get('code') == 404 and detail.get('status') == 'NOT_FOUND':
            return None
        if conflict and error.code == 409 and isinstance(detail, dict) and detail.get('code') == 409 and detail.get('status') == 'ALREADY_EXISTS':
            return None
        raise RuntimeError('API HTTP ' + str(error.code) + '; permission/absence not established') from None


def ar(method, resource, **kwargs):
    return api(method, 'https://artifactregistry.googleapis.com/v1/' + resource, **kwargs)


def canonical_resource(value):
    if isinstance(value, str) and value.startswith('projects/' + PROJECT_NUMBER + '/'):
        return 'projects/' + PROJECT + value[len('projects/' + PROJECT_NUMBER):]
    return value


def parse_version(name):
    name = canonical_resource(name)
    prefix = PACKAGE + '/versions/'
    require(isinstance(name, str) and name.startswith(prefix), 'Version belongs to another package/project')
    digest = urllib.parse.unquote(name[len(prefix):])
    require(bool(re.fullmatch(r'sha256:[0-9a-f]{64}', digest)), 'Invalid immutable digest')
    return digest


def tag_digest():
    resource = PACKAGE + '/tags/' + SOURCE_SHA
    tag = ar('GET', resource, absent=True)
    if tag is None:
        return None
    require(canonical_resource(tag.get('name')) == resource, 'Unexpected exact tag')
    return parse_version(tag.get('version'))


def require_no_previous_build():
    """Build-once guard for the exact application SHA across control revisions."""
    run_id = int(os.environ['GITHUB_RUN_ID'])
    control_sha = os.environ['GITHUB_SHA']
    expected_title = 'Publish Dation ' + SOURCE_SHA
    base = 'https://api.github.com/repos/nicsejara/Dation/actions/'
    for page in range(1, 11):
        result = api('GET', base + f'workflows/runtime-v2-publish.yml/runs?event=workflow_dispatch&per_page=100&page={page}', github=True)
        runs = result.get('workflow_runs')
        require(isinstance(runs, list), 'Actions run history unavailable')
        for run in runs:
            if int(run['id']) >= run_id:
                continue
            title = run.get('display_title')
            if title != expected_title:
                require(title or run.get('head_sha') != control_sha,
                    'Unidentifiable earlier dispatch of these release controls')
                continue
            require(run.get('status') == 'completed', 'Earlier manual publication of this SHA is unresolved')
            jobs = api('GET', base + f'runs/{run["id"]}/jobs?filter=all&per_page=100', github=True)
            require(isinstance(jobs.get('jobs'), list) and isinstance(jobs.get('total_count'), int) and
                jobs['total_count'] == len(jobs['jobs']) and jobs['total_count'] <= 100, 'Actions job history incomplete')
            for job in jobs['jobs']:
                steps = job.get('steps', [])
                require(isinstance(steps, list), 'Actions step history unavailable')
                require(any(step.get('name') == TRUST['build_step_name'] for step in steps) or
                    job.get('conclusion') in ('failure', 'cancelled', 'skipped'), 'Earlier successful job has unrecognized build history')
                for step in steps:
                    if step.get('name') == TRUST['build_step_name']:
                        require(step.get('conclusion') == 'skipped', 'A previous build was attempted; recover its image or diagnose before rebuilding')
        if len(runs) < 100:
            return
    raise RuntimeError('Actions history exceeds the verifiable window; no new build')


def install_crane(output):
    binary = output / 'tools/crane'
    if not binary.exists():
        archive = output / 'tools/crane.tar.gz'; archive.parent.mkdir(exist_ok=True)
        command('curl', '--fail', '--silent', '--show-error', '--location', '--proto', '=https',
            '--max-time', '120', '--output', archive, CRANE_URL, timeout=125)
        require(digest_file(archive) == CRANE_ARCHIVE_SHA, 'Crane archive checksum mismatch')
        with tarfile.open(archive) as tar:
            member = tar.getmember('crane'); require(member.isfile(), 'Invalid crane archive')
            binary.write_bytes(tar.extractfile(member).read()); binary.chmod(0o700)
    require(digest_file(binary) == CRANE_SHA, 'Crane binary checksum mismatch')
    return binary


def login():
    auth = Path(os.environ['DOCKER_CONFIG']); auth.mkdir(mode=0o700, parents=True, exist_ok=True)
    command('docker', 'login', '--username', 'oauth2accesstoken', '--password-stdin', HOST,
        secret_input=os.environ['DATION_PUBLISH_ACCESS_TOKEN'] + '\n')



def validate_green_source(source):
    """Require exact ancestor of the trusted main control SHA and same-SHA gate."""
    control = Path(os.environ['GITHUB_WORKSPACE']) / 'control'
    require(command('git', '-C', control, 'rev-parse', 'HEAD') == os.environ['GITHUB_SHA'],
        'Release controls differ from trusted dispatch commit')
    command('git', '-C', control, 'cat-file', '-e', SOURCE_SHA + '^{commit}')
    command('git', '-C', control, 'merge-base', '--is-ancestor', SOURCE_SHA, 'HEAD')
    require(command('git', '-C', source, 'rev-parse', 'HEAD') == SOURCE_SHA,
        'Checkout SHA differs from requested application')
    url = 'https://api.github.com/repos/nicsejara/Dation/commits/' + SOURCE_SHA + '/check-runs?per_page=100'
    result = api('GET', url, github=True)
    checks = result.get('check_runs', [])
    require(isinstance(checks, list) and isinstance(result.get('total_count'), int) and
        result['total_count'] == len(checks) and result['total_count'] <= 100,
        'Incomplete check-run evidence for selected SHA')
    matching = [c for c in checks if c.get('name') == 'required-gate' and
                c.get('head_sha') == SOURCE_SHA and c.get('status') == 'completed']
    require(len(matching) == 1 and matching[0].get('conclusion') == 'success',
        'No unique successful required-gate check on exact application SHA')

def preflight(source, output):
    source_check(source, output)
    validate_green_source(source)
    repository = ar('GET', REPOSITORY)
    require(canonical_resource(repository.get('name')) == REPOSITORY and repository.get('format') == 'DOCKER' and
        repository.get('mode') in (None, 'STANDARD_REPOSITORY'), 'Unexpected Registry identity/type')
    require(repository.get('vulnerabilityScanningConfig', {}).get('enablementConfig') != 'ENABLED', 'Scanning enabled: unreviewed cost')
    rights = ar('POST', REPOSITORY + ':testIamPermissions', body={'permissions': sorted(PERMISSIONS)})
    require(set(rights.get('permissions', [])) == PERMISSIONS, 'Publisher lacks repository-scoped permissions; no broader IAM fallback')
    # Only an exact immutable SHA tag identifies this release.
    # The repository intentionally retains previous releases for rollback.
    digest = tag_digest()
    if digest is None:
        require_no_previous_build()
    else:
        login(); crane = install_crane(output)
        config = json.loads(command(crane, 'config', IMAGE + '@' + digest))
        require(config.get('architecture') == 'amd64' and config.get('os') == 'linux' and
            config.get('config', {}).get('Labels', {}).get('org.opencontainers.image.revision') == SOURCE_SHA,
            'Existing image identity is not the validated baseline; never overwrite')
    state = {'source_sha': SOURCE_SHA, 'build_required': digest is None, 'digest': digest,
             'local_image': 'dation-gate-c:' + SOURCE_SHA, 'source_dockerfile_sha256': digest_file(source / 'Dockerfile')}
    write(output / 'state.json', state)
    outputs(build_required=str(state['build_required']).lower())


def build(source, output):
    state = json.loads((output / 'state.json').read_text())
    require(state['build_required'] and not (output / 'build.started').exists(), 'Build already claimed or unnecessary')
    with (output / 'build.started').open('x') as stream:
        stream.write(datetime.now(timezone.utc).isoformat())
    command('docker', 'build', '--platform', 'linux/amd64', '--label', 'org.opencontainers.image.revision=' + SOURCE_SHA,
        '--iidfile', output / 'image-id.txt', '--tag', state['local_image'], source, timeout=1200)


def verify_image(output):
    state = json.loads((output / 'state.json').read_text())
    image = state['local_image'] if state['build_required'] else IMAGE + '@' + state['digest']
    if not state['build_required']:
        command('docker', 'pull', '--platform', 'linux/amd64', image, timeout=120)
    fields = command('docker', 'image', 'inspect', image, '--format',
        '{{.Id}} {{.Os}} {{.Architecture}} {{index .Config.Labels "org.opencontainers.image.revision"}} {{.Size}}').split()
    require(len(fields) == 5 and fields[1:4] == ['linux', 'amd64', SOURCE_SHA] and int(fields[4]) <= 2 * 1024**3,
        'Image revision/architecture/size mismatch')
    if state['build_required']:
        require((output / 'image-id.txt').read_text().strip() == fields[0], 'Built image was replaced')
    for args in (['-m', 'pip', 'check'], ['-c', 'import main; from app.services import execution_dispatch; print("imports_ok")']):
        command('docker', 'run', '--rm', '--network', 'none', '--cpus=1', '--memory=512m',
            '--entrypoint', 'python', image, *args)
    state.update(image_id=fields[0], size_bytes=int(fields[4]), dependencies_verified=True, imports_verified=True)
    write(output / 'state.json', state)


def create_tag(digest):
    current = tag_digest()
    require(current in (None, digest), 'Exact tag changed identity; never overwrite')
    if current is None:
        resource = PACKAGE + '/tags?tagId=' + SOURCE_SHA
        result = ar('POST', resource, body={'version': PACKAGE + '/versions/' + digest}, conflict=True)
        if result is not None:
            require(canonical_resource(result.get('name')) == PACKAGE + '/tags/' + SOURCE_SHA and
                parse_version(result.get('version')) == digest, 'Created tag identity mismatch')
        require(tag_digest() == digest, 'Concurrent tag differs or metadata is not yet verified; no overwrite')


def manifests(source, output, pinned):
    spec = importlib.util.spec_from_file_location('validated_release', source / 'scripts/zero_idle_release.py')
    release = importlib.util.module_from_spec(spec); spec.loader.exec_module(release)
    plan = json.loads((source / 'infra/zero-idle/release.json').read_text())
    plan.update(release_sha=SOURCE_SHA, image=pinned)
    plan['secret_references'].pop('DATION_ACCESS_PASSWORD', None)
    release.validate(plan)
    generated = release.manifest(plan)
    generated['service']['scaling'] = {'minInstanceCount': 0, 'maxInstanceCount': 2}
    generated['service']['template']['containers'][0]['resources']['startupCpuBoost'] = False
    for name, value in {'release.json': plan, 'api.json': generated['service'], 'executor.json': generated['jobs'][0],
        'recovery.json': generated['jobs'][1], 'dispatcher-role.json': generated['iam']['custom_role']['role']}.items():
        write(output / 'manifests' / name, value)


def publish(source, output):
    state = json.loads((output / 'state.json').read_text())
    require(state.get('dependencies_verified') and state.get('imports_verified'), 'Image checks did not pass')
    login(); crane = install_crane(output)
    digest = state['digest']
    if state['build_required']:
        require(tag_digest() is None, 'Exact SHA tag appeared during the build; no unexpected publication')
        archive = output / 'image.tar'
        command('docker', 'save', '--output', archive, state['image_id'], timeout=120)
        digest = command(crane, 'digest', '--tarball', archive, timeout=180)
        require(bool(re.fullmatch(r'sha256:[0-9a-f]{64}', digest)), 'Invalid local manifest digest')
        with (output / 'publication.started').open('x') as stream:
            stream.write(digest)
        command(crane, 'push', archive, IMAGE + '@' + digest, timeout=300)
    pinned = IMAGE + '@' + digest
    require(command(crane, 'digest', pinned) == digest, 'Remote immutable digest differs')
    manifest = json.loads(command(crane, 'manifest', pinned))
    require(manifest.get('config', {}).get('digest') == state['image_id'], 'Remote config differs from verified local image')
    create_tag(digest)
    require(tag_digest() == digest and command(crane, 'digest', TAG) == digest, 'Exact remote tag/digest mismatch')
    manifests(source, output, pinned)
    receipt = {'phase': 'C', 'status': 'PASS', 'milestone': 'GO_C_IMAGE_PUBLISHED', 'project': PROJECT,
        'project_number': PROJECT_NUMBER, 'region': REGION, 'sha': SOURCE_SHA, 'image_digest': pinned,
        'architecture': 'amd64', 'image_id': state['image_id'], 'image_size_bytes': state['size_bytes'],
        'source_dockerfile_sha256': state['source_dockerfile_sha256'], 'control_sha': os.environ['GITHUB_SHA'], 'workflow_sha': os.environ['GITHUB_SHA'],
        'workflow_ref': os.environ['GITHUB_WORKFLOW_REF'], 'run_id': os.environ['GITHUB_RUN_ID'],
        'run_url': 'https://github.com/nicsejara/Dation/actions/runs/' + os.environ['GITHUB_RUN_ID'],
        'publisher_account': ACCOUNT, 'identity_provider': PROVIDER, 'authentication': 'OIDC WIF, short-lived SA token',
        'built_this_run': state['build_required'], 'dependencies_verified': True, 'imports_verified': True,
        'cloud_build_used': False, 'cloud_build_api_state': 'OFF per accepted owner evidence; publisher has no service-management permissions',
        'migration_version': '20261109215204', 'cloud_run_deployed': False, 'jobs_executed': 0,
        'scheduler_activated': False, 'apply_unlocked': False, 'receipt_at_utc': datetime.now(timezone.utc).isoformat()}
    write(output / 'GATE_C_RECEIPT.json', receipt)
    print(json.dumps(receipt, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('guard', 'preflight', 'build', 'verify', 'publish'))
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); os.umask(0o077); args.output.mkdir(parents=True, exist_ok=True)
    try:
        guard_context()
        if args.phase == 'guard':
            outputs(provider=PROVIDER, audience='https://iam.googleapis.com/' + PROVIDER, service_account=ACCOUNT)
        else:
            require(args.source is not None, 'Source checkout required')
            source_check(args.source, args.output)
            if args.phase == 'preflight': preflight(args.source, args.output)
            elif args.phase == 'build': build(args.source, args.output)
            elif args.phase == 'verify': verify_image(args.output)
            else: publish(args.source, args.output)
        write(args.output / 'GATE_C_STATUS.json', {'phase': args.phase, 'status': 'PASS', 'source_sha': SOURCE_SHA})
    except Exception as error:
        message = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        write(args.output / 'GATE_C_STATUS.json', {'phase': args.phase, 'status': 'NO_GO', 'reason': message, 'source_sha': SOURCE_SHA})
        print('NO_GO: ' + message, file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
