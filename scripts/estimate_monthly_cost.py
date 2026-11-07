"""Reproducible USD scenarios; conservative shared-credit allocation defaults to zero."""
import argparse
from dataclasses import dataclass,asdict,replace
import json
import math

RATES={'api_cpu':.000024,'api_gib':.0000025,'job_cpu':.000018,'job_gib':.000002,
       'api_request':.40/1_000_000,'scheduler':.10,'registry_gib':.10,
       'build_minute':.006,'log_gib':.50,'secret_version':.06,'secret_access':.03/10000}

@dataclass(frozen=True)
class Scenario:
    name:str='custom'
    pilots:int=1
    pairs_per_day:int=5
    workdays:int=22
    calendar_days:int=30
    d1_wall_seconds:float=65
    d2_wall_seconds:float=5
    comparative_per_pair:float=.25
    comparative_wall_seconds:float=5
    compute_gib:float=1
    compute_cpu:float=1
    case_jobs_per_pair:float=4
    case_wall_seconds:float=2
    recovery_interval_minutes:int=15
    recovery_wall_seconds:float=2
    control_gib:float=.5
    extra_activation_attempts:float=0
    api_allocated_seconds_per_pair:float=6
    api_read_requests:int=1000
    api_read_allocated_seconds:float=.1
    api_requests_per_pair:int=12
    api_gib:float=.5
    registry_gib:float=1
    build_minutes:float=20
    log_gib:float=.05
    secret_versions:int=3
    secret_accesses:int=3000
    egress_gib:float=.1
    egress_usd_per_gib:float=.12
    supabase_monthly_usd:float=0
    netlify_monthly_usd:float=0
    llm_input_mtokens:float=0
    llm_output_mtokens:float=0
    llm_input_usd_per_million:float=0
    llm_output_usd_per_million:float=0


def estimate(s,credits=None):
    values=asdict(s)
    if any(v<0 for k,v in values.items() if isinstance(v,(int,float))):raise ValueError('Negative usage')
    if s.recovery_interval_minutes<1:raise ValueError('Recovery interval must be positive')
    if s.extra_activation_attempts>2:raise ValueError('Delivery retries bounded to three attempts')
    pairs=s.pilots*s.pairs_per_day*s.workdays
    recovery=math.ceil(s.calendar_days*24*60/s.recovery_interval_minutes)
    compute_seconds=pairs*(max(60,s.d1_wall_seconds)+max(60,s.d2_wall_seconds)+s.comparative_per_pair*max(60,s.comparative_wall_seconds))
    compute_seconds+=pairs*(2+s.comparative_per_pair)*s.extra_activation_attempts*60
    control_seconds=pairs*s.case_jobs_per_pair*max(60,s.case_wall_seconds)*(1+s.extra_activation_attempts)+recovery*max(60,s.recovery_wall_seconds)
    api_seconds=pairs*s.api_allocated_seconds_per_pair+s.api_read_requests*s.api_read_allocated_seconds
    requests=pairs*s.api_requests_per_pair+s.api_read_requests
    gross={
        'cloud_run_job_cpu':(compute_seconds*s.compute_cpu+control_seconds)*RATES['job_cpu'],
        'cloud_run_job_ram':(compute_seconds*s.compute_gib+control_seconds*s.control_gib)*RATES['job_gib'],
        'cloud_run_api_cpu':api_seconds*RATES['api_cpu'],
        'cloud_run_api_ram':api_seconds*s.api_gib*RATES['api_gib'],
        'cloud_run_requests':requests*RATES['api_request'],
        'scheduler':RATES['scheduler'],
        'artifact_registry':s.registry_gib*RATES['registry_gib'],
        'cloud_build':s.build_minutes*RATES['build_minute'],
        'cloud_logging':s.log_gib*RATES['log_gib'],
        'secret_versions':s.secret_versions*RATES['secret_version'],
        'secret_access':s.secret_accesses*RATES['secret_access'],
        'network_egress':s.egress_gib*s.egress_usd_per_gib,
    }
    # CPU and RAM credits are ONE billing-account pool across request/instance SKUs.
    available=credits or {};ceilings={'cpu':4.32,'ram':.90,'requests':.80,'scheduler':.30,
        'registry':.05,'build':15,'logging':25,'secret_versions':.36,'secret_access':.03}
    if any(k not in ceilings or v<0 or v>ceilings[k] for k,v in available.items()):raise ValueError('Unverified/excess credit allocation')
    applied={k:0.0 for k in gross}
    groups={'cpu':['cloud_run_job_cpu','cloud_run_api_cpu'],'ram':['cloud_run_job_ram','cloud_run_api_ram'],
        'requests':['cloud_run_requests'],'scheduler':['scheduler'],'registry':['artifact_registry'],
        'build':['cloud_build'],'logging':['cloud_logging'],'secret_versions':['secret_versions'],'secret_access':['secret_access']}
    for group,skus in groups.items():
        remaining=available.get(group,0)
        for sku in skus:applied[sku]=min(remaining,gross[sku]);remaining-=applied[sku]
    net={k:gross[k]-applied[k] for k in gross}
    external={'supabase':s.supabase_monthly_usd,'netlify':s.netlify_monthly_usd,
        'llm':s.llm_input_mtokens*s.llm_input_usd_per_million+s.llm_output_mtokens*s.llm_output_usd_per_million}
    return {'scenario':values,'region':'us-west1','currency':'USD','price_checked':'2026-11-05 America/Buenos_Aires',
        'usage':{'pairs':pairs,'compute_task_seconds_billed':compute_seconds,'control_task_seconds_billed':control_seconds,
                 'api_instance_seconds_allocated':api_seconds,'recovery_ticks':recovery},
        'gcp':{'gross':gross,'allocated_credits':applied,'net':net,'gross_total':sum(gross.values()),'net_total':sum(net.values())},
        'external':external,'estimated_total_usd':sum(net.values())+sum(external.values()),
        'limitations':['Illustrative usage, not live P50/P95 or billing evidence','Jobs billed at least 60 seconds per task',
            'API uses allocated instance wall time, not process CPU time; adjust concurrent request overlap',
            'Shared free quotas default UNALLOCATED; account availability must be verified',
            'Network input is a parameter, not a universal/free egress assertion',
            'Extra delivery startup is charged even when duplicate work is fenced; this is not a hard spending cap',
            'External plan prices/LLM tokens and platform usage require separate owner inputs; taxes excluded']}


def scenarios():
    base=Scenario()
    return [replace(base,name='idle_control_plane',pilots=0,api_read_requests=0),
        replace(base,name='5_pairs_22_workdays'),replace(base,name='5_pairs_30_calendar_days',workdays=30),
        replace(base,name='3_pilots',pilots=3),replace(base,name='10_pilots',pilots=10),
        replace(base,name='10_pilots_adverse_retries',pilots=10,extra_activation_attempts=2,d1_wall_seconds=120),
        replace(base,name='long_job_2Gi_sensitivity',d1_wall_seconds=300,compute_gib=2)]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',help='JSON object with Scenario fields')
    p.add_argument('--credits',help='JSON verified available credit allocation in USD, e.g. {"cpu":1}')
    args=p.parse_args();credits=json.loads(args.credits) if args.credits else None
    inputs=[Scenario(**json.loads(args.input))] if args.input else scenarios()
    print(json.dumps([estimate(s,credits) for s in inputs],indent=2))

if __name__=='__main__':main()
