# Dation Rapid Development — pilot checklist

Status: NOT EXECUTED. This file is a test plan, not completion evidence.

Pilot A: harmless isolated CSS rule (R1)
- FAST gate; FULL skipped.
- Measure change->gate and verify UI visually.

Pilot B: minor Core Configuration/Decision Graph interaction (R2)
- FAST plus browser smoke of Case/model/contract and D1 readiness.
- No editor changes to publisher constants for a new SHA.
- GitHub manual publish; Cloud Run prepare, smoke, explicit promote; rollback.

Capture: PR/head/merge SHA, exact gate check/status, tests/risk, image digest,
GitHub run/receipt, revisions and traffic, number of human steps, measured
time (p50/p90 over repeated runs), and actual cost if billing metrics exist.

Only declare DATION_RAPID_DEV_READY after BOTH pilots pass with measured
evidence. No productive D1/D2 jobs or Supabase writes in CI.