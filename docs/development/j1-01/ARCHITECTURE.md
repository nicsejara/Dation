# J1.01 architecture and integrity

```text
existing models/index.mjs
  ├─ server capability OFF → existing legacy library/editor
  └─ server capability ON → model-library.mjs
       ├─ real list / filtered paginated metadata
       ├─ model-library-editor → existing mountModelFields → unchanged R6
       │    ├─ working copy (browser UUID, authenticated subject scope)
       │    └─ explicit controller → existing checked create / update / publish
       ├─ exact Library Review → shared R6 historical projection
       └─ History → exact published version IDs

Core / Graph → normalized return token → Library → original Core context
                                     (no Case draft or candidate writes)
```

## Identity and states

| Entity | Identity / state | Authority |
|---|---|---|
| Family | `model_id`, active/archived, mutable draft revision | Existing checked RPC |
| Published version | `version_id`, version number, config/contract hashes | Append-only SQL snapshot |
| Working copy | `model_work_id`, independent model draft/checkpoint/intents | Browser recovery, scoped user/workspace |
| UI mode | library / edit / review / history | Validated resource route; never permission |
| Return context | `model_return_id` UUID | Scoped session token containing normalized internal resource |
| Case | Existing `case_id` and pinned version | Existing Case API; library never mutates it |

Working copies use `dation.models.working.v1.<workspace>.<user>.<workId>`.
There is no `model.new` singleton and no access to `case.new`. A browser Web Lock
owns each mounted working copy. Another tab can read the library but cannot edit
the same copy until it is released. Distinct copies of one server model use SQL
`expected_revision` CAS. Browser revisions/storage events additionally detect
unexpected external changes. Browsers without Web Locks cannot open a mutable
working copy; they receive an explicit error instead of an unsafe fallback.

The session bootstrap previously erased all model storage in a fresh tab. The
bounded fix preserves only the authenticated subject's exact local copy prefix
when the tab has no prior identity. Foreign prefixes, ordinary transient state,
logout and identity changes retain the existing clearing behavior. VM tests prove
both recovery and clearing. Access/refresh tokens are never stored in model data.

## Mutation protocol

1. Explicit **Guardar borrador** with incomplete R6: save checkpoint in this
   browser only; no model API write. Recovery changes remain distinct from an
   explicitly saved checkpoint. Saving does not publish.
2. Valid draft: persist the exact create/update intent before sending. Creation
   uses its stable family UUID. Update uses its original expected revision.
3. A response must confirm the model identity and expected next revision.
   Replayed creation returning an advanced revision is rejected as conflict;
   it cannot silently adopt another client's changed draft.
4. Five R6 confirmations and current server preview are required for a fresh
   publication. A pending **save** cannot bypass them. Persist a fixed publication
   UUID/revision before POST. A pending publication retries this exact identity.
5. Only matching server version/model, positive version number and SHA-256 hash
   acknowledge publication. Network failure retains the original intent and
   freezes editing. There is no implicit mutation retry.
6. A 409 preserves the copy and original revision. Explicit reload requires a
   confirmation and discards only that copy, never a published snapshot or Case.

New publication retries resolve before mutable draft validation in existing SQL.
An unresolved publication conflict deliberately remains blocked; do not delete
its recovery state or generate a replacement intent blindly. Compare its exact
UUID with server History, retain the copy, and resolve deliberately.

## Reads, routing and compatibility

Library Review explicitly sets `reviewContext=library`; Case Review defaults to
`case_pinned`. The same R6 projection renders original snapshots in both contexts.
Library omits Case metadata and derivation actions. Pinned Review retains its
existing CTA, dimensions and exact version. Legacy snapshots are read without
normalization, JSON editing or default insertion.

Search is server-backed **name** search. The library reads 50-item API pages,
checks total/duplicate/incomplete-page consistency, and filters/paginates the
complete metadata set in 25-card pages. A concurrent list change requests a fresh
read rather than silently omitting/duplicating rows. Order remains the API's
updated-at/ID order; no unsupported sort is advertised.

Resource IDs are validated UUIDs; review requires an explicit existing version.
Return tokens can contain only normalized views/IDs in the same application.
They are user/workspace scoped, cannot be arbitrary URLs, and grant no authority.
Lost return context disables continuation rather than inventing a new Case.
The existing router still owns history, scope disposal and cancellation. Dirty
model exits offer Save / Discard / Continue; cancellation reverts browser history.

No change to SQL, the Data Contract compiler, physical calculations, D1/D2,
execution admission, preparation, approvals, Case schemas or deployment policy.
