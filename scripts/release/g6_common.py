"""G6 bounded transports and immutable Actions checkpoints. No IAM mutations."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from dation_release import PROJECT, REGION, SERVICE, REGISTRY, SHA_RE, DIGEST_RE, require

ROOT = Path(__file__).resolve().parents[2]
POLICY_FILE = ROOT / 'infra/zero-idle/ux-autopilot-policy.json'
POLICY = json.loads(POLICY_FILE.read_text())
REPO = POLICY['repository']
RESOURCE = f'projects/{PROJECT}/locations/{REGION}/services/{SERVICE}'
PROVIDER = f"projects/{POLICY['project_number']}/locations/global/workloadIdentityPools/{POLICY['pool']}/providers/{POLICY['provider']}"
DEPLOYER = POLICY['deployer_account'] + '@' + PROJECT + '.iam.gserviceaccount.com'
AUTO_PATH = '.github/workflows/' + POLICY['auto_workflow']
OPS_PATH = '.github/workflows/' + POLICY['ops_workflow']


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def fingerprint(value): return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def outputs(**values):
    with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
        for key, value in values.items():
            require('\n' not in str(value), 'multiline output denied')
            stream.write(f'{key}={value}\n')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None


class HttpError(RuntimeError):
    def __init__(self, code, status):
        self.code = code; self.status = status
        super().__init__(f'NO_GO: remote HTTP {code} {status}; no permission expansion or retry')


def request(method, url, token, body=None, missing=False):
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(), method=method,
        headers={'Authorization': 'Bearer ' + token, 'Accept':'application/vnd.github+json' if urllib.parse.urlsplit(url).hostname=='api.github.com' else 'application/json', 'Content-Type':'application/json'})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=45) as response:
            raw = response.read(32 * 1024 * 1024 + 1)
            require(len(raw) <= 32 * 1024 * 1024, 'response too large')
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        try: detail = json.loads(error.read(65536)).get('error', {})
        except (ValueError, AttributeError): detail = {}
        if not isinstance(detail, dict): detail = {}
        if missing and error.code == 404 and detail.get('code') == 404 and detail.get('status') == 'NOT_FOUND': return None
        raise HttpError(error.code, detail.get('status', 'UNVERIFIED')) from None


class GitHub:
    def __init__(self, token=None): self.token = token if token is not None else os.environ['GH_TOKEN']
    def api(self, path, method='GET', body=None):
        require(path.startswith('/') and not path.startswith('//') and '..' not in path and '\n' not in path, 'invalid repository API path')
        return request(method, 'https://api.github.com/repos/' + REPO + path, self.token, body)
    def pages(self, path, field=None):
        result = []
        for page in range(1, 21):
            value = self.api(path + ('&' if '?' in path else '?') + f'per_page=100&page={page}')
            rows = value[field] if field else value
            require(isinstance(rows, list), 'incomplete API collection')
            result.extend(rows)
            if len(rows) < 100:
                if field and 'total_count' in value: require(len(result) == value['total_count'], 'incomplete paginated evidence')
                return result
        raise RuntimeError('NO_GO: collection exceeds verified window')
    def main(self):
        branch = self.api('/branches/main')
        return branch['commit']['sha']
    def protected(self):
        branch = self.api('/branches/main')
        require(branch.get('protected') is True, 'main protection is not verified')
        # Public metadata endpoint for effective branch rules; errors are NO_GO.
        rules = self.api('/rules/branches/main')
        require(isinstance(rules,list), 'branch rules unavailable')
        checks = [r for r in rules if r.get('type') == 'required_status_checks']
        require(any(any(c.get('context') == 'required-gate' for c in r.get('parameters',{}).get('required_status_checks',[])) for r in checks), 'required-gate must be an enforced branch rule')
        reviews = [r for r in rules if r.get('type') == 'pull_request']
        require(any(r.get('parameters',{}).get('require_code_owner_review') is True for r in reviews), 'critical paths need enforced CODEOWNERS review')
        owners = ROOT / '.github/CODEOWNERS'
        require(owners.is_file(), 'CODEOWNERS missing')
        entries = {line.split()[0]:line.split()[1:] for line in owners.read_text().splitlines() if line and not line.startswith('#')}
        require(all(entries.get(path) == ['@nicsejara'] for path in POLICY['required_codeowner_paths']), 'critical CODEOWNERS coverage differs')
    def run(self, run_id, workflow, sha=None, terminal=True):
        require(re.fullmatch(r'[0-9]+', str(run_id)), 'invalid run ID')
        run = self.api('/actions/runs/' + str(run_id))
        require(run.get('repository',{}).get('id') == POLICY['repository_id'] and run.get('head_repository',{}).get('id') == POLICY['repository_id'] and
            run.get('path') == '.github/workflows/' + workflow and run.get('head_branch') == 'main', 'untrusted workflow provenance')
        if sha: require(run.get('head_sha') == sha, 'run belongs to another SHA')
        if terminal: require(run.get('status') == 'completed' and run.get('conclusion') == 'success', 'workflow is not terminal GREEN')
        return run
    def gate(self, run_id, sha, risk=None):
        run = self.run(run_id, POLICY['gate_workflow'], sha)
        require(run.get('event') == 'push' and run.get('name') == 'Dation FAST gate', 'main push gate required')
        history = self.pages('/actions/workflows/' + POLICY['gate_workflow'] + '/runs?event=push&head_sha=' + sha, 'workflow_runs')
        require(history and str(max(history, key=lambda r: int(r['id']))['id']) == str(run_id),
            'a newer pending/failing gate exists; older GREEN cannot authorize a release')
        jobs = self.pages('/actions/runs/' + str(run_id) + '/jobs?filter=latest', 'jobs')
        for name in ('impact','fast','required-gate'):
            matches = [j for j in jobs if j.get('name') == name]
            require(len(matches) == 1 and matches[0].get('status') == 'completed' and matches[0].get('conclusion') == 'success' and
                bool(matches[0].get('steps')), 'missing/failing/ambiguous required step: ' + name)
            required = {'impact':['Classify actual diff (fail closed)'], 'fast':['Verify impact classifier and fail-closed routing','Static checks for changed JS / Python / CSS / JSON'], 'required-gate':['Enforce expected successful checks']}[name]
            if name == 'fast' and risk == 'R2': required.append('Business-path browser smoke (R2 only)')
            require(all(any(s.get('name') == label and s.get('conclusion') == 'success' for s in matches[0]['steps']) for label in required), 'required step did not pass')
        full = [j for j in jobs if j.get('name') == 'full']
        require(len(full) == 1 and full[0].get('conclusion') == 'skipped', 'only R1/R2 gates with FULL legitimately skipped')
        return run
    def archive(self, artifact):
        require(not artifact.get('expired') and artifact.get('size_in_bytes',0) <= 32*1024*1024, 'artifact unavailable/too large')
        req = urllib.request.Request('https://api.github.com/repos/' + REPO + '/actions/artifacts/' + str(artifact['id']) + '/zip', headers={'Authorization':'Bearer ' + self.token})
        try:
            with urllib.request.build_opener(NoRedirect()).open(req,timeout=45) as response: raw=response.read(32*1024*1024+1)
        except urllib.error.HTTPError as error:
            require(error.code == 302, 'artifact redirect is not verified')
            url = error.headers.get('Location',''); parsed = urllib.parse.urlsplit(url)
            require(parsed.scheme == 'https' and not parsed.username and not parsed.password and parsed.hostname and
                parsed.hostname.endswith(('.blob.core.windows.net','.githubusercontent.com','.actions.githubusercontent.com')), 'unexpected artifact storage origin')
            # Never forward the GitHub token to storage, or follow a second redirect.
            with urllib.request.build_opener(NoRedirect()).open(url,timeout=45) as response: raw=response.read(32*1024*1024+1)
        require(len(raw)<=32*1024*1024 and 'sha256:' + hashlib.sha256(raw).hexdigest() == artifact.get('digest'), 'artifact ZIP digest mismatch')
        return raw
    def artifact(self, run_id, name, optional=False):
        items = self.pages('/actions/runs/' + str(run_id) + '/artifacts?name=' + urllib.parse.quote(name), 'artifacts')
        if not items and optional: return None
        require(len(items)==1 and items[0].get('name')==name, 'missing or ambiguous immutable checkpoint: ' + name)
        with zipfile.ZipFile(io.BytesIO(self.archive(items[0]))) as archive:
            names = archive.namelist()
            require(names and len(names)==len(set(names)) and len(names)<=12 and all(not n.startswith('/') and '..' not in Path(n).parts and '\\' not in n and n.endswith('.json') for n in names), 'unsafe checkpoint members')
            require(sum(i.file_size for i in archive.infolist())<=4*1024*1024, 'checkpoint expansion too large')
            return {name:json.loads(archive.read(name)) for name in names}


class CloudRun:
    def __init__(self, token=None, read_only=False, tools=None):
        self.tools=Path(tools) if tools else None
        self.token = token if token is not None else os.environ['DATION_DEPLOY_TOKEN']
        self.read_only = read_only
    def api(self, resource=RESOURCE, method='GET', body=None, query='', missing=False):
        require(resource == RESOURCE or resource.startswith(RESOURCE + '/revisions/') or resource in (RESOURCE + ':getIamPolicy', RESOURCE + ':testIamPermissions'), 'only the existing API service/revision can be accessed')
        probe = method=='POST' and resource==RESOURCE+':testIamPermissions' and body=={'permissions':POLICY['service_permissions']}
        require(probe or method == 'GET' or method == 'PATCH' and resource == RESOURCE and not self.read_only and query in ('template,traffic','traffic'), 'Cloud Run mutation outside approved scope')
        url = 'https://run.googleapis.com/v2/' + resource
        if method == 'PATCH':
            require(body and body.get('name') == RESOURCE and body.get('etag') and set(body)<= {'name','etag','template','traffic'}, 'missing CAS or unexpected update')
            url += '?updateMask=' + query
        elif resource.endswith(':getIamPolicy'): url += '?options.requestedPolicyVersion=3'
        return request(method, url, self.token, body, missing)
    def iam(self): return self.api(RESOURCE + ':getIamPolicy')
    def permission_probe(self):
        rights=self.api(RESOURCE+':testIamPermissions',method='POST',body={'permissions':POLICY['service_permissions']})
        require(set(rights.get('permissions',[]))==set(POLICY['service_permissions']), 'service-scoped deploy permissions are not effective')
        account='dation-runtime@'+PROJECT+'.iam.gserviceaccount.com'
        result=request('POST','https://iam.googleapis.com/v1/projects/'+PROJECT+'/serviceAccounts/'+account+':testIamPermissions',self.token,{'permissions':['iam.serviceAccounts.actAs']})
        require(result.get('permissions')==['iam.serviceAccounts.actAs'],'runtime actAs is not effective')
    def application_sha(self, image):
        require(self.tools is not None and image.startswith(REGISTRY+'@') and DIGEST_RE.fullmatch(image.split('@')[-1]), 'OCI read requires pinned image and isolated tools directory')
        require(os.environ.get('DOCKER_CONFIG') and Path(os.environ['DOCKER_CONFIG']).resolve() != self.tools.resolve(), 'isolated registry auth directory required')
        # Reuse the publisher's checksummed crane client; no build, push or new dependency.
        import importlib.util
        spec=importlib.util.spec_from_file_location('g6_readonly_registry',ROOT/'scripts/runtime_v2_publication.py')
        publisher=importlib.util.module_from_spec(spec);spec.loader.exec_module(publisher)
        self.tools.mkdir(parents=True,exist_ok=True)
        prior=os.environ.get('DATION_PUBLISH_ACCESS_TOKEN')
        os.environ['DATION_PUBLISH_ACCESS_TOKEN']=self.token
        try:
            publisher.login();binary=publisher.install_crane(self.tools)
            config=json.loads(publisher.command(binary,'config',image))
        finally:
            if prior is None:os.environ.pop('DATION_PUBLISH_ACCESS_TOKEN',None)
            else:os.environ['DATION_PUBLISH_ACCESS_TOKEN']=prior
        sha=config.get('config',{}).get('Labels',{}).get('org.opencontainers.image.revision','')
        require(config.get('architecture')=='amd64' and config.get('os')=='linux' and SHA_RE.fullmatch(sha),'deployed OCI revision/architecture cannot be verified')
        self.registry(sha,image)
        return sha

    def registry(self, sha, image):
        require(SHA_RE.fullmatch(sha) and image.startswith(REGISTRY + '@') and DIGEST_RE.fullmatch(image.split('@')[-1]), 'invalid immutable image')
        package = f"projects/{PROJECT}/locations/{REGION}/repositories/dation-runtime/packages/dation-core"
        tag = request('GET','https://artifactregistry.googleapis.com/v1/' + package + '/tags/' + sha,self.token)
        resource = str(tag.get('version','')).replace("projects/"+POLICY['project_number']+'/', 'projects/'+PROJECT+'/')
        require(urllib.parse.unquote(resource) == package + '/versions/' + image.split('@')[1], 'Registry exact SHA tag differs from published receipt')


def context(mode='auto', env=os.environ):
    expected = {'GITHUB_ACTIONS':'true','GITHUB_REPOSITORY':REPO,'GITHUB_REPOSITORY_ID':str(POLICY['repository_id']),
        'GITHUB_REPOSITORY_OWNER_ID':str(POLICY['owner_id']),'GITHUB_REF':'refs/heads/main','GITHUB_RUN_ATTEMPT':'1',
        'GITHUB_EVENT_NAME':'workflow_run' if mode == 'auto' else 'workflow_dispatch',
        'GITHUB_WORKFLOW_REF':REPO + '/' + (AUTO_PATH if mode=='auto' else OPS_PATH) + '@refs/heads/main'}
    require(all(env.get(k)==v for k,v in expected.items()), 'untrusted execution context or rerun')
    require(re.fullmatch(r'[0-9]+',env.get('GITHUB_RUN_ID','')), 'missing own run identity')
    require(SHA_RE.fullmatch(env.get('GITHUB_SHA','')), 'missing control commit')


def validate_plan(plan):
    require(plan.get('application_sha') and SHA_RE.fullmatch(plan['application_sha']) and
        plan.get('repository_id')==POLICY['repository_id'] and plan.get('policy_sha256')==hashlib.sha256(POLICY_FILE.read_bytes()).hexdigest() and
        plan.get('release_id')=='g6-' + str(plan.get('release_run_id')) and re.fullmatch(r'[0-9]+',str(plan.get('release_run_id',''))), 'plan identity/policy mismatch')
    require(plan.get('status') == 'ELIGIBLE', 'release has not passed eligibility')
    return plan


def download_plan(gh, run_id):
    require(re.fullmatch(r'[0-9]+',str(run_id or '')), 'invalid checkpoint run ID')
    run=gh.api('/actions/runs/'+str(run_id))
    path=run.get('path')
    require(path in (AUTO_PATH,OPS_PATH),'checkpoint from untrusted workflow')
    gh.run(run_id,path.rsplit('/',1)[1],terminal=False)
    require(run.get('event')==('workflow_run' if path==AUTO_PATH else 'workflow_dispatch'),'checkpoint event mismatch')
    bundle=gh.artifact(run_id,'g6-plan-'+str(run_id))
    plan=validate_plan(bundle['plan.json'])
    origin=gh.run(plan['release_run_id'],POLICY['auto_workflow'],plan['application_sha'],terminal=False)
    require(origin.get('event')=='workflow_run','origin is not trusted autorelease')
    if path==AUTO_PATH:require(plan['release_run_id']==str(run_id) and plan['application_sha']==run['head_sha'],'plan/run commit mismatch')
    return plan
