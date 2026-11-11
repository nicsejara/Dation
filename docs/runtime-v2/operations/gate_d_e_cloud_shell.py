"""One authorized GO WEB intervention. Exact Gate C manifests; never runs Jobs."""
import base64
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

PROJECT = 'dation-runtime-v2-2026'
NUMBER = '332279365872'
REGION = 'us-west1'
APP_SHA = '792470ff8cce54cb32b81240b206fdbcb7078ea2'
RUN = '42942509569'
DIGEST = 'sha256:e99f10d1efd3acb45a97f8da936b787a700b54daf52c481151cfa5738e4cf36d'
IMAGE = f'us-west1-docker.pkg.dev/{PROJECT}/dation-runtime/dation-core@{DIGEST}'
BASE = f'projects/{PROJECT}/locations/{REGION}'
RUNTIME = f'dation-runtime@{PROJECT}.iam.gserviceaccount.com'
MEMBER = 'serviceAccount:' + RUNTIME
ROLE = f'projects/{PROJECT}/roles/dationFiniteJobDispatcher'
SERVICE = BASE + '/services/dation-core'
JOBS = [BASE + '/jobs/dation-executor', BASE + '/jobs/dation-recovery']
ZIP_SHA = '282c24eec8044e096f74e38888bee35b5618ad20aa4b5004053181498c9644f4'
# Byte-identical official artifact, not regenerated manifests or a build context.
ARTIFACT_BASE64 = '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'
STATE = Path.home() / ('dation-go-web-' + RUN)
SENSITIVE = []


def need(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def now(): return datetime.now(timezone.utc).isoformat()


def save(name, data):
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    (STATE / name).write_text(json.dumps(data, indent=2) + '\n')


def load(name):
    p = STATE / name
    return json.loads(p.read_text()) if p.exists() else None


def gc(*args, raw=False):
    result = subprocess.run(['gcloud', *args, '--project=' + PROJECT, '--billing-project=' + PROJECT, '--quiet',
        *([] if raw else ['--format=json'])], capture_output=True, text=True, timeout=120)
    if result.returncode:
        message = result.stderr[-2000:]
        for secret in SENSITIVE: message = message.replace(secret, '[REDACTED]')
        raise RuntimeError('gcloud ' + ' '.join(args[:3]) + ': ' + message)
    return result.stdout.strip() if raw else json.loads(result.stdout or 'null')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None


class ApiFailure(RuntimeError):
    def __init__(self, code, detail):
        self.code = code; self.detail = detail
        reasons = [d.get('reason') for d in detail.get('details', []) if isinstance(d, dict)]
        super().__init__('API HTTP ' + str(code) + ' ' + str(detail.get('status')) + ' reasons=' + repr(reasons))


def api(method, url, body=None, absent=False, conflict=False):
    host = urllib.parse.urlsplit(url).netloc
    allowed = (
        host == 'run.googleapis.com' and url.startswith('https://run.googleapis.com/v2/' + BASE + '/') or
        host == 'iam.googleapis.com' and url.startswith('https://iam.googleapis.com/v1/projects/' + PROJECT + '/') or
        host == 'artifactregistry.googleapis.com' and url.startswith('https://artifactregistry.googleapis.com/v1/projects/' + PROJECT + '/locations/' + REGION + '/repositories/dation-runtime') or
        host == 'billingbudgets.googleapis.com' and method == 'GET' and '/budgets?' in url and
            'scope=projects%2F' + NUMBER in url)
    need(allowed and ':run' not in url, 'Unapproved API destination or Job execution')
    token = gc('auth', 'print-access-token', raw=True)
    SENSITIVE.append(token)
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(), method=method,
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json', 'x-goog-user-project':PROJECT})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=60) as response:
            value = json.load(response); need(isinstance(value, dict), 'Ambiguous API result'); return value
    except urllib.error.HTTPError as error:
        try: detail = json.loads(error.read(65536)).get('error', {})
        except (ValueError, AttributeError): detail = {}
        if not isinstance(detail, dict): detail = {}
        if absent and error.code == 404 and detail.get('code') == 404 and detail.get('status') == 'NOT_FOUND': return None
        if conflict and error.code == 409 and detail.get('code') == 409 and detail.get('status') == 'ALREADY_EXISTS': return None
        raise ApiFailure(error.code, detail) from None


def run_api(method, resource, **kwargs):
    return api(method, 'https://run.googleapis.com/v2/' + resource, **kwargs)


def all_items(resource, field):
    result = []; page = ''
    for _ in range(100):
        response = run_api('GET', resource + '?' + urllib.parse.urlencode({'pageSize':100, 'pageToken':page}))
        values = response.get(field, []); need(isinstance(values, list), 'Ambiguous resource list')
        result.extend(values); page = response.get('nextPageToken', '')
        if not page: return result
    raise RuntimeError('Incomplete resource inventory')


def canonical(name):
    if isinstance(name, str) and name.startswith('projects/' + NUMBER + '/'):
        return 'projects/' + PROJECT + name[len('projects/' + NUMBER):]
    return name


def grant_roles(policy, member):
    found = [b for b in policy.get('bindings', []) if member in b.get('members', [])]
    need(not any(b.get('condition') for b in found), 'Unexpected conditional IAM grant')
    return {b['role'] for b in found}


def no_public_jobs(policy):
    need(not any(set(b.get('members', [])) & {'allUsers', 'allAuthenticatedUsers'} for b in policy.get('bindings', [])), 'Public Job IAM forbidden')


def policy(resource):
    return run_api('GET', resource + ':getIamPolicy?options.requestedPolicyVersion=3')


def bind(resource, role, member, remove=False):
    need((resource in JOBS and role == ROLE and member == MEMBER and not remove) or
        (resource == SERVICE and role == 'roles/run.invoker' and member == 'allUsers'), 'Unapproved IAM delta')
    current = policy(resource)
    if resource in JOBS: no_public_jobs(current)
    updated = copy.deepcopy(current)
    found = False
    for b in updated.get('bindings', []):
        if b['role'] == role and not b.get('condition'):
            found = True
            if remove: b['members'] = [m for m in b['members'] if m != member]
            elif member not in b['members']: b['members'].append(member)
    if not found and not remove: updated.setdefault('bindings', []).append({'role':role, 'members':[member]})
    updated['bindings'] = [b for b in updated.get('bindings', []) if b.get('members')]
    if updated == current: return False
    save(resource.rsplit('/', 1)[1] + '-iam-before.json', current)
    run_api('POST', resource + ':setIamPolicy', body={'policy':updated})
    verified = policy(resource)
    need((role not in grant_roles(verified, member)) if remove else (role in grant_roles(verified, member)), 'IAM delta not verified')
    if resource in JOBS: no_public_jobs(verified)
    return True


def artifact():
    data = base64.b64decode(ARTIFACT_BASE64, validate=True)
    need(hashlib.sha256(data).hexdigest() == ZIP_SHA, 'Official Gate C ZIP checksum mismatch')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        expected = {'GATE_C_RECEIPT.json','GATE_C_STATUS.json', *['manifests/' + n + '.json' for n in ('api','executor','recovery','dispatcher-role','release')]}
        need(set(archive.namelist()) == expected and len(archive.namelist()) == 7, 'Unexpected official artifact members')
        documents = {name:json.loads(archive.read(name)) for name in expected}
    receipt = documents['GATE_C_RECEIPT.json']
    need(receipt['status'] == 'PASS' and receipt['sha'] == APP_SHA and receipt['run_id'] == RUN and
        receipt['image_digest'] == IMAGE and receipt['project'] == PROJECT and receipt['architecture'] == 'amd64' and
        receipt['workflow_sha'] == '3297db4eb41a70abc44fec7c1d0db35cc6e1892a', 'Receipt identity mismatch')
    # Keep all artifact documents byte/content-identical. Never call release.py apply.
    return {k.removeprefix('manifests/').removesuffix('.json'):v for k,v in documents.items() if k.startswith('manifests/')}


def check_spec(actual, expected, service=False):
    need(canonical(actual.get('name')) == expected['name'], 'Resource identity mismatch')
    def check_container(container, wanted):
        need(container.get('image') == IMAGE and container.get('command') == wanted['command'] and
            container.get('args', []) == wanted.get('args', []), 'Image or process command differs')
        env = copy.deepcopy(container.get('env', []))
        for entry in env:
            ref = entry.get('valueSource', {}).get('secretKeyRef')
            if ref:
                for project in (PROJECT, NUMBER):
                    prefix = 'projects/' + project + '/secrets/'
                    if ref.get('secret', '').startswith(prefix): ref['secret'] = ref['secret'][len(prefix):]
        need(sorted(env, key=lambda e:e['name']) == sorted(wanted['env'], key=lambda e:e['name']), 'Environment or Secret Manager references differ')
        resources = container.get('resources', {})
        need(resources.get('limits') == wanted['resources']['limits'], 'CPU/memory mismatch')
        if service: need(resources.get('cpuIdle', True) and not resources.get('startupCpuBoost', False), 'Continuous CPU or startup boost forbidden')
    if service:
        template = actual['template']; wanted = expected['template']
        for scale in (actual.get('scaling', {}), template.get('scaling', {})):
            need(scale.get('minInstanceCount', 0) == 0 and scale.get('maxInstanceCount') == 2, 'Service/revision scale-to-zero limits differ')
        need(template.get('serviceAccount') == RUNTIME and template.get('timeout') == '300s' and
            template.get('maxInstanceRequestConcurrency') == 8, 'API identity or limits differ')
        need(not actual.get('invokerIamDisabled', False) and not template.get('vpcAccess') and not template.get('volumes'), 'Unapproved API IAM/network/storage')
    else:
        outer = actual['template']; template = outer['template']; wanted = expected['template']['template']
        need(outer.get('taskCount', 1) == 1 and outer.get('parallelism', 1) == 1 and
            template.get('maxRetries', 0) == 0 and template.get('timeout') == wanted['timeout'] and
            template.get('serviceAccount') == RUNTIME and not template.get('vpcAccess') and not template.get('volumes'), 'Finite Job limits differ')
        need(actual.get('executionCount', 0) == 0, 'A Job has already executed; stop')
    need(len(template.get('containers', [])) == 1, 'Unexpected sidecar/resident process')
    check_container(template['containers'][0], wanted['containers'][0])


def wait_operation(operation):
    name = operation['name']; need(name.startswith(BASE + '/operations/'), 'Operation outside Runtime V2')
    deadline = time.monotonic() + 600
    while True:
        if operation.get('done'):
            need('error' not in operation, 'Cloud Run operation failed: ' + str(operation.get('error')))
            return
        need(time.monotonic() < deadline, 'Operation still active; rerun resumes saved operation, never rebuilds')
        time.sleep(3); operation = run_api('GET', name)


def ensure_resource(expected, service=False):
    name = expected['name']; key = name.rsplit('/', 1)[1]
    pending = load(key + '-operation.json')
    if pending: wait_operation(pending)
    current = run_api('GET', name, absent=True)
    if current is None:
        need(not load(key + '-creation-started.json'), 'Previous creation has no resolved resource/operation; inspect before retry')
        save(key + '-creation-started.json', {'at':now(), 'name':name, 'image':IMAGE})
        kind = 'services' if service else 'jobs'; id_key = 'serviceId' if service else 'jobId'
        operation = run_api('POST', BASE + '/' + kind + '?' + id_key + '=' + key, body=expected, conflict=True)
        if operation:
            save(key + '-operation.json', operation); wait_operation(operation)
        current = run_api('GET', name)
    check_spec(current, expected, service)
    save(key + '-verified.json', current)
    return current


def db_closed():
    secret = gc('secrets','versions','access','1','--secret=dation-supabase-secret',raw=True)
    need(bool(secret), 'Empty Supabase secret'); SENSITIVE.append(secret)
    req = urllib.request.Request('https://gijiinufjjurgfeehufj.supabase.co/rest/v1/rpc/execution_runtime',
        data=json.dumps({'operation':'policy','arguments':{}}).encode(),
        headers={'apikey':secret, 'Authorization':'Bearer ' + secret, 'Content-Type':'application/json'}, method='POST')
    try:
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=30) as response: value = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError('Runtime Supabase policy read HTTP ' + str(error.code) + '; no changes made to Supabase') from None
    need(value.get('enabled') is False and value.get('admissions_open') is False, 'D1/D2 admissions are not closed')
    return {'enabled':False, 'admissions_open':False}


def finops(billing):
    account = billing.get('billingAccountName', '')
    need(re.fullmatch(r'billingAccounts/[A-Z0-9-]+',account), 'Billing account identity unavailable')
    url = 'https://billingbudgets.googleapis.com/v1/' + account + '/budgets?' + urllib.parse.urlencode({'scope':'projects/' + NUMBER,'pageSize':100})
    try:
        result = api('GET', url)
        need(not result.get('nextPageToken'), 'Budget inventory incomplete')
        cap = [b for b in result.get('budgets', []) if b.get('budgetFilter', {}).get('projects') in (['projects/' + NUMBER], ['projects/' + PROJECT]) and
            b.get('budgetFilter', {}).get('services') == ['services/152E-C115-5142'] and b.get('spendCap')]
        need(len(cap) == 1, 'Exact project/Cloud Run spend cap not identified')
        budget = cap[0]; amount = budget.get('amount', {}).get('specifiedAmount', {})
        need(amount.get('currencyCode') == 'USD' and int(amount.get('units', 0)) == 5 and int(amount.get('nanos', 0)) == 0 and
            budget['spendCap'].get('outputState') == 'CONFIGURED' and not budget['spendCap'].get('reconciling'), 'Spend cap is not configured at USD5; no budget changes allowed')
        return {'source':'Cloud Billing Budget API', 'state':'CONFIGURED', 'usd':5,'scope':'Cloud Run only, not a total or guaranteed cap'}
    except ApiFailure as error:
        if error.code != 403: raise
        print(str(error), flush=True)
        print('Budget read unavailable. Do not enable APIs or grant roles. Verify current Cloud Run cap USD5 CONFIGURED in the owner console.', flush=True)
        print('Only if verified now, type CONFIGURED USD5 RUN_ONLY; otherwise Enter stops: ', end='', flush=True)
        with open('/dev/tty') as terminal: answer = terminal.readline().strip()
        need(answer == 'CONFIGURED USD5 RUN_ONLY', 'Current spend cap not verified; zero deploy changes')
        return {'source':'Owner console confirmation in this Cloud Shell session','state':'CONFIGURED','usd':5,
            'api_read':'HTTP403, not verified via API', 'scope':'Cloud Run only, not a total or guaranteed cap'}


def preflight(manifests):
    identity = gc('projects','describe',PROJECT)
    need((identity.get('projectId'),identity.get('projectNumber'),identity.get('lifecycleState')) == (PROJECT,NUMBER,'ACTIVE'), 'GCP project identity mismatch')
    billing = gc('billing','projects','describe',PROJECT)
    need(billing.get('billingEnabled') is True, 'Billing is not enabled; never enable it in this procedure')
    enabled = {s.get('config',{}).get('name') for s in gc('services','list','--enabled')}
    need({'run.googleapis.com','artifactregistry.googleapis.com','secretmanager.googleapis.com','iam.googleapis.com'} <= enabled, 'Required API disabled; do not enable automatically')
    need(not {'cloudbuild.googleapis.com','cloudscheduler.googleapis.com'} & enabled, 'Cloud Build/Scheduler must remain OFF; do not change them here')
    economic = finops(billing)
    account = gc('iam','service-accounts','describe',RUNTIME)
    need(account.get('email') == RUNTIME and not account.get('disabled'), 'Runtime service account mismatch')
    project_policy = gc('projects','get-iam-policy',PROJECT)
    need(not grant_roles(project_policy, MEMBER), 'Unexpected project-wide runtime roles')
    agent = 'serviceAccount:service-' + NUMBER + '@serverless-robot-prod.iam.gserviceaccount.com'
    need(grant_roles(project_policy,agent) <= {'roles/run.serviceAgent'}, 'Unexpected managed Run Service Agent roles')
    # First resource creation may provision the managed service agent automatically.
    # Never add its role by speculation; verify it after the platform creates resources.
    need(not any(set(b.get('members', [])) & {'allUsers','allAuthenticatedUsers'} for b in project_policy.get('bindings', [])), 'Public project IAM forbidden')
    version = gc('secrets','versions','describe','1','--secret=dation-supabase-secret')
    need(version.get('state') == 'ENABLED', 'Secret Manager version1 is not enabled')
    secret_policy = gc('secrets','get-iam-policy','dation-supabase-secret')
    need('roles/secretmanager.secretAccessor' in grant_roles(secret_policy,MEMBER), 'Runtime secret access not verified')
    rights = api('POST', 'https://iam.googleapis.com/v1/projects/' + PROJECT + '/serviceAccounts/' + RUNTIME + ':testIamPermissions', body={'permissions':['iam.serviceAccounts.actAs']})
    need('iam.serviceAccounts.actAs' in rights.get('permissions',[]), 'Operator actAs missing on runtime account')
    services = all_items(BASE + '/services','services'); jobs = all_items(BASE + '/jobs','jobs')
    need(all(canonical(s['name']) == SERVICE for s in services) and all(canonical(j['name']) in JOBS for j in jobs), 'Unexpected existing Run service/Job; inspect only the unexpected resource')
    for job in jobs:
        name = canonical(job['name']); check_spec(job,manifests['executor' if name == JOBS[0] else 'recovery'])
        no_public_jobs(policy(name));need(not all_items(name + '/executions','executions'), 'Existing Job execution detected')
    for service in services:
        check_spec(service,manifests['api'],True)
        if 'roles/run.invoker' in grant_roles(policy(SERVICE),'allUsers'):
            need(load('public-access-verified.json') or load('public-grant-started.json'), 'Existing public API was not published by this procedure')
    database = db_closed()
    save('preflight.json',{'at':now(),'project':PROJECT,'billing_enabled':True,'economic':economic,
        'services':[canonical(x['name']) for x in services],'jobs':[canonical(x['name']) for x in jobs], 'database':database,
        'cloud_build_api':'DISABLED','scheduler_api':'DISABLED','secret_version':'1'})
    return economic


def ensure_role(expected):
    url = 'https://iam.googleapis.com/v1/' + ROLE
    current = api('GET',url,absent=True)
    if current is None:
        api('POST','https://iam.googleapis.com/v1/projects/' + PROJECT + '/roles',body={'roleId':'dationFiniteJobDispatcher','role':expected},conflict=True)
        current = api('GET',url)
    need(set(current.get('includedPermissions',[])) == set(expected['includedPermissions']) and
        not current.get('deleted') and current.get('stage') == 'GA', 'Dispatcher role differs from official artifact')


def web_request(url, path, identity=None, invalid_bearer=False):
    headers = {'User-Agent':'Dation-GO-WEB-verifier'}
    if identity: headers['X-Serverless-Authorization'] = 'Bearer ' + identity
    if invalid_bearer: headers['Authorization'] = 'Bearer deliberately-invalid-go-web-token'
    req = urllib.request.Request(url + path, headers=headers)
    try:
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=90) as r: return r.status, r.headers, r.read(150000)
    except urllib.error.HTTPError as error: return error.code, error.headers, error.read(150000)


def verify_web(url, identity=None):
    status, _, body = web_request(url,'/health',identity)
    need(status == 200 and json.loads(body).get('status') == 'healthy', 'API health did not pass')
    for invalid in (False, True):
        status, headers, body = web_request(url,'/api/datasets',identity,invalid)
        try: detail = json.loads(body).get('detail')
        except (ValueError,AttributeError): detail = None
        need(status == 401 and isinstance(detail,str) and bool(detail) and 'application/json' in headers.get('Content-Type',''), 'Business authentication not proven: expected application JSON401')
    status, _, body = web_request(url,'/login',identity)
    need(status == 200 and b'<html' in body.lower(), 'Login page did not render')
    status, headers, _ = web_request(url,'/app',identity)
    need(status in (302,303,307) and headers.get('Location','').startswith('/login'), 'Anonymous app navigation is not protected')
    return {'health':'PASS','missing_bearer':'JSON401','invalid_bearer':'JSON401','login_page':'200','anonymous_app':'redirect_login'}


def gate_d(manifests, economic):
    ensure_role(manifests['dispatcher-role'])
    for kind,name in [('executor',JOBS[0]),('recovery',JOBS[1])]:
        print('Creating/verifying finite Job ' + name.rsplit('/',1)[1] + ' (never executes)',flush=True)
        ensure_resource(manifests[kind]);bind(name,ROLE,MEMBER)
        need(grant_roles(policy(name),MEMBER) == {ROLE}, 'Unexpected additional runtime Job grants')
        need(not all_items(name + '/executions','executions'), 'Job execution detected')
    print('Creating/verifying private API at exact immutable digest',flush=True)
    service = ensure_resource(manifests['api'],True)
    project_policy = gc('projects','get-iam-policy',PROJECT)
    agent = 'serviceAccount:service-' + NUMBER + '@serverless-robot-prod.iam.gserviceaccount.com'
    need('roles/run.serviceAgent' in grant_roles(project_policy,agent), 'Managed Run Service Agent grant not verified after creation')
    need(not service.get('reconciling') and service.get('latestReadyRevision') == service.get('latestCreatedRevision'), 'API revision is not ready')
    revision = canonical(service['latestReadyRevision']);need(revision.startswith(SERVICE + '/revisions/'), 'Revision belongs to another service')
    actual = run_api('GET',revision)
    # Revision has the same limits/container fields as Service.template.
    expected = manifests['api'];check_spec({'name':SERVICE,'scaling':service['scaling'],'template':actual},expected,True)
    revisions = all_items(SERVICE + '/revisions','revisions')
    need(all(r.get('scaling',{}).get('minInstanceCount',0) == 0 for r in revisions), 'A revision has minimum instances')
    need(not any(t.get('tag') or canonical(t.get('revision')) not in (None,revision) for t in service.get('trafficStatuses',[])), 'Unexpected traffic tag/revision')
    url = service.get('uri','').rstrip('/')
    parsed = urllib.parse.urlsplit(url)
    need(parsed.scheme == 'https' and parsed.hostname and parsed.hostname.endswith('.run.app') and
        parsed.port in (None,443) and not parsed.path and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment, 'URL is not an HTTPS URI returned by Cloud Run')
    identity = gc('auth','print-identity-token',raw=True);SENSITIVE.append(identity)
    negative = verify_web(url,identity)
    receipt = {'phase':'D','status':'PASS','milestone':'GO_D_CLOUD_RUN_DEPLOYED','at':now(), 'project':PROJECT,
        'application_sha':APP_SHA,'image_digest':IMAGE,'source_run':RUN,'official_artifact_sha256':ZIP_SHA,
        'url':url,'revision':revision,'service_min_instances':0,'service_max_instances':2,'cpu_idle':True,
        'secret_version':'1','DATION_CLOUD_EXECUTION_ENABLED':False,'database':db_closed(),'jobs_executed':0,
        'job_iam':'exact 3-permission custom role scoped only to both Jobs; metadata verified',
        'runtime_job_token_probe':'not run; no impersonation grants or Job executions added',
        'scheduler':'API DISABLED, not configured','apply_unlocked':False,'economic':economic,
        'platform_authorized_business_auth_checks':negative,'private_first':True,
        'actual_instance_count_after_idle':'NOT_MEASURED; min0 configuration verified, not an instantaneous zero-instance claim'}
    save('GATE_D_RECEIPT.json',receipt)
    print(json.dumps(receipt,indent=2),flush=True)
    return url


def public_api(url):
    # This Gate E substep is authorized only after the Gate D receipt exists.
    need(load('GATE_D_RECEIPT.json'), 'Gate D receipt missing')
    save('public-grant-started.json',{'url':url,'at':now(),'image':IMAGE})
    changed = bind(SERVICE,'roles/run.invoker','allUsers')
    try:
        checks = verify_web(url)
        receipt = {'phase':'E','status':'PARTIAL','milestone':'GO_E_PUBLIC_API_AUTH_CHECKED',
            'url':url,'web_url':url + '/app','image_digest':IMAGE,'checks':checks,
            'database':db_closed(),'auth_redirects':'PENDING_CODEX_SUPABASE_PATCH',
            'real_user_login_logout_navigation':'PENDING_REAL_BROWSER','jobs_executed':0,'at':now()}
        save('public-access-verified.json',receipt);save('GATE_E_ACCESS_RECEIPT.json',receipt)
        print(json.dumps(receipt,indent=2),flush=True)
    except Exception:
        if changed: bind(SERVICE,'roles/run.invoker','allUsers',remove=True)
        raise


def main():
    os.umask(0o077)
    need(os.environ.get('DATION_GO_WEB') == 'GO_WEB_D_E_RUN42942509569', 'Existing explicit GO WEB required; no writes performed')
    STATE.mkdir(mode=0o700,parents=True,exist_ok=True)
    lock = STATE / 'operator.lock'
    import fcntl
    with lock.open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            manifests = artifact()
            economic = preflight(manifests)
            url = gate_d(manifests,economic)
            public_api(url)
            save('NEXT_ACTION.json',{'url':url,'next':'Return GATE_D_RECEIPT and GATE_E_ACCESS_RECEIPT only; Codex updates Supabase Auth and verifies real login/navigation','not_web_live_yet':True})
        except Exception as error:
            reason = str(error)
            for secret in SENSITIVE: reason = reason.replace(secret,'[REDACTED]')
            save('GATE_DE_STATUS.json',{'status':'NO_GO','reason':reason,'at':now(),'state_dir':str(STATE),
                'note':'No automatic deletion/rebuild/republication. Resources may exist; retain receipts and operation markers.'})
            raise SystemExit('NO_GO: ' + reason) from None


if __name__ == '__main__':main()
