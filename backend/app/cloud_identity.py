"""Pinned Runtime V2 identity, shared by the runtime and offline release tools.

No discovery, credentials or network calls. Cloud execution requires every
identity field explicitly; environment defaults never select a cloud project.
"""
import re

PROJECT = 'dation-runtime-v2-2026'
PROJECT_NUMBER = '332279365872'
REGION = 'us-west1'
SERVICE = 'dation-core'
JOBS = {
    'compute': f'projects/{PROJECT}/locations/{REGION}/jobs/dation-executor',
    'control': f'projects/{PROJECT}/locations/{REGION}/jobs/dation-recovery',
}
RUNTIME_ACCOUNT_ID = 'dation-runtime'
SCHEDULER_ACCOUNT_ID = 'dation-scheduler'
RUNTIME_ACCOUNT = f'{RUNTIME_ACCOUNT_ID}@{PROJECT}.iam.gserviceaccount.com'
SCHEDULER_ACCOUNT = f'{SCHEDULER_ACCOUNT_ID}@{PROJECT}.iam.gserviceaccount.com'


def environment():
    return {
        'DATION_CLOUD_PROJECT': PROJECT,
        'DATION_CLOUD_PROJECT_NUMBER': PROJECT_NUMBER,
        'DATION_CLOUD_REGION': REGION,
        'DATION_COMPUTE_JOB': JOBS['compute'],
        'DATION_CONTROL_JOB': JOBS['control'],
    }


def validate_environment(values):
    for key, expected in environment().items():
        if values.get(key) != expected:
            raise ValueError(f'Missing or unexpected Runtime V2 identity: {key}')
    # Optional provider metadata must agree when supplied, too.
    if values.get('GOOGLE_CLOUD_PROJECT', PROJECT) != PROJECT:
        raise ValueError('Provider project conflicts with Runtime V2')


def validate_account(value):
    if not isinstance(value, str) or not re.fullmatch(
        r'[a-z][a-z0-9-]{4,28}[a-z0-9]@' + re.escape(PROJECT) + r'\.iam\.gserviceaccount\.com', value
    ):
        raise ValueError('Service account must belong to Runtime V2')


def validate_image(value):
    if value == 'REQUIRES_REVIEWED_IMAGE_DIGEST':
        return  # Offline plan only; apply remains blocked for all plans.
    prefix = f'{REGION}-docker.pkg.dev/{PROJECT}/'
    if not isinstance(value, str) or not re.fullmatch(
        re.escape(prefix) + r'[a-z0-9][a-z0-9._-]*(?:/[a-z0-9][a-z0-9._-]*)+@sha256:[0-9a-f]{64}', value
    ):
        raise ValueError('Image must be a Runtime V2 regional Registry digest')
