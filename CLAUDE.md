# CLAUDE.md — Project operating rules

This project follows **4-layer document-driven development**.
**All user-facing output — responses, generated specification documents, reports — MUST be
in Japanese.** Code, identifiers, and shell commands are in English.

## Document system principles (most important)

Terminology: the numbered 4 layers directly under `docs/` (00-requests/ / 01-requirements/ /
02-design/ / 03-impl/) are collectively called **「仕様ドキュメント」(specification documents)**.
When referring to 03-impl alone, always write "03-impl".

1. **The specification documents are the Single Source of Truth: they always describe the
   system as it should currently be.** Update in place. This includes 00-requests: additional
   requests are appended via /change, and **requests contradicting existing text REWRITE the
   old text** — never keep both (the withdrawn intent survives in histories and git).
   request.md is authored in the human's words; decisions.md is a ledger the human approves.
   The AI may draft diffs to either, but human agreement is mandatory for the whole 00 layer.
   Never write execution plans, tasks, or TODOs in specification documents.
2. **Granularity differs per layer. The module split is an OUTPUT of design.**
   - 00-requests: one directory for the whole system — the requirements package (usually
     produced with the upstream requirements kit). Files: `request.md` (WHY; the human's
     words; mandatory), `decisions.md` (the decision ledger: every pre-triaged judgment as
     決定/委任/要確認; mandatory), `glossary.md`, `acceptance.md` (user-language acceptance
     scenarios, AS-n; an upstream seed of 01's UCs), `examples/` (concrete samples; no
     frontmatter, not versioned). Downstream docs list the package files they draw on in
     `source` (01 lists at least request.md and decisions.md).
   - 01-requirements: start as one file; split by **business domain** when large (WHAT).
     Includes ユースケース (UC-n): actor journeys spanning requirements — the upstream
     source E2E test scenarios are derived from.
   - 02-design: `system.md` (overall design) is mandatory. **The module split is defined
     here** (the モジュール分割定義 table). Large modules may add `<module>.md` detail designs.
     The テスト戦略 section covers all 3 levels (単体/結合/E2E): integration-test ownership
     per contract, and the E2Eシナリオ一覧 derived from 01's use cases.
   - 03-impl: **one file per module**, following the 分割定義 in `02-design/system.md`.
     Never create a 03-impl for a module not in the 分割定義. Sole standard exception:
     `03-impl/e2e.md` (source: system.md), governed by the E2Eシナリオ一覧 — create it when
     scenarios exist; never implement an E2E test for a scenario not in the 一覧.
3. **`verified` is a certificate of passing.** /doc-check writes it into the frontmatter of
   a document that passed verification: when (at), which version of itself (version), and
   which upstream versions (against) it passed for. ONLY /doc-check may write it (there is
   no status field).
   **Version is MAJOR.MINOR.PATCH**: semantic changes (requirements, contracts, behavior,
   structure) bump MINOR or higher; meaning-preserving edits (typos, wording, formatting)
   bump PATCH only. **When in doubt, bump MINOR** (safe side).
   **Verified — the single rule**: the certificate exists, and the versions written in it
   match the current versions (self and every upstream) on **MAJOR.MINOR**. Any edit that
   shifts a version automatically voids the certificate (= unverified, re-check needed).
   PATCH changes do not void it. Invalidation propagates DOWNWARD only (the edited doc and
   anything having it in `source`; never upward). Never generate or update a document unless
   ALL of its `source` documents are verified — with two bounded exceptions: **inside one phase-2
   descent**, where the closure is edited top-down and certification is deferred to the closing
   `/doc-check` (that is the point of "certify last"), and **`/reverse-doc`**, which bootstraps a
   chain from existing code and therefore creates 03→02→01 with no verified upstream at all; the
   chain is then certified upstream-first (00→03) by `/doc-check`. Outside those two, the rule is
   absolute.
   **Cascade control** — four rules; re-running /doc-check once per layer is this system's
   dominant cost and most of it is self-inflicted (details: `/doc-check`):
   - **One bump per phase**: a document bumps ONCE, when the phase's edits are finished.
   - **Certify last**: write `verified` only after every document in the closure holds its final
     version — never while the set is still moving.
   - **Converge inside the run**: a certificate voided by an edit made in THIS phase belongs to
     THIS phase's closure. Ending a run with a lapse you caused yourself is a defect.
   - **Delta verification**: when a document's own body is unchanged since its last PASS and it
     lapsed only because an upstream version moved, the obligation is the upstream DELTA × this
     document. Delta out of its reach → refresh the `against` versions, keep the certificate, no
     bump, no history entry. /doc-check only; unidentifiable delta → full verification.
4. **`docs/histories/` is the change history of documents** (all specification documents
   plus steering). One entry per change reason (`YYYY-MM-DD-<slug>.md`); record every updated
   document in affected, each with a specific per-document `change:` line (delta verification reads
   it). First editions start at 1.0.0 and need no entry; PATCH-only edits need none either.
   Append-only — **with one clarification: adding rows to `affected`, or updating an existing row's
   version transition to its final value, for the SAME change reason is part of appending** (that is
   how a phase-3 03-impl sync is recorded). A different reason means a new entry; a confirmed entry's
   prose is never rewritten. **Never write tasks or progress here.**
5. **`docs/tasks/<work-slug>.md` is the AI's working document — one file per work** (see the Phase
   model for what a work is). Exactly two roles: (a) persisting progress across sessions, (b)
   holding the work's Definition of Done. It exists from the moment the work is identified (so a
   queued, not-yet-implemented work has one too — `phase: ドキュメント`) until its implementation
   completes. Not subject to human approval. **Delete on completion — and also on abort** (git
   keeps the trail; document changes are already in history). **Deleting it IS the completion claim,
   so it goes through the gate, never `rm`**: `python3 .claude/scripts/close-task.py <work-slug>`
   refuses while any document in the 影響範囲 is lapsed (`--abort` for the abort path, which reports
   the lapse instead of blocking). Everything in it is working state, and its
   調査メモ is a **derived cache, never an SSOT** (the SSOTs are the specification documents and
   the code): cite `path:line`, let the code win any conflict, never make it a `source:`. Before
   deleting, route what is durable — module facts → 03-impl, cross-cutting premises →
   steering/tech.md, lessons and traps → `docs/knowledge/` — and discard the rest deliberately.
6. **Code ⇄ 03-impl consistency is an invariant.** When you change code, update the module's
   03-impl (and upstream if needed) within the same work. On discovering divergence, report
   it and ask the human which side is correct.
7. **A document is deep enough only when implementing it requires deciding nothing.**
   Plausible-but-shallow prose is the root cause of rework: the gap surfaces during
   implementation and drags the work back up the layers, so depth is a verified property.
   - **実装ドライラン, in this order.** Pass 1 (documents ONLY — no code, no web): derive the task
     breakdown and the test list, and enumerate every point where you would have to DECIDE
     something to proceed. Each such **未決点** is closed as: written into the document / decided
     inside a 委任 (with its D-n) / put on the phase's decision sheet. Two lenses run pass 1: you,
     and an independent agent (`/codex-audit readiness`). Pass 2 (technical investigation — code,
     tests, libraries): resolve the FACTS the breakdown needs and write them into the task
     document's 調査メモ so phase 3 does not re-derive them. Order is mandatory: investigating
     first makes you fill spec gaps from code and under-report 未決点. A fact found in code never
     closes a 未決点 — if code and 03-impl disagree, that is a check-B divergence.
     Checks: `/doc-check` D11–D13.
   - **未決点ゼロ is the entry condition for implementation.** /implement refuses to start while
     an unclosed 未決点 remains in its chain. 未決点 live in the task document, never in a
     specification document (an unresolvable one becomes 未解決事項, which blocks verification).

## Phase model — one work, three phases, one attended point

A work (a change, or the next build step) runs as THREE phases. Phase 1 is the only SCHEDULED
attended point; phases 2 and 3 contact the human at most ONCE each, at their end, and only if
items are still open — never mid-phase, never one question at a time. Bouncing between layers and
skills mid-work — fix, check, implement, fix again, check again — is the failure mode this model
prevents.

| Phase | Skill | Human | Must be finished before leaving the phase |
|---|---|---|---|
| 1 決定 | `/change` (or `/gen` at a layer boundary) | attends, ONCE | the **closure** (every document across 00–03 this work will touch) and the **decision sheet(決定シート)**: every question of the whole work asked in ONE batch, each item answered / delegated (→ a 委任 entry in decisions.md with guardrails) / explicitly deferred |
| 2 ドキュメント深掘り | the descent inside `/change`, or `/gen` → then `/doc-check` | none, unless items remain → ONE sheet at the phase's end | the closure edited top-down in ONE descent, 実装ドライラン run and every 未決点 closed, versions bumped once, `verified` written across the whole closure |
| 3 実装 | `/implement` | none, unless items remain → ONE sheet at the phase's end | code and tests green, 03-impl synced, ONE final re-certification |

Rules that make phases 2 and 3 actually unattended:

- **Batch every question.** A phase asks at most once, at its end — immediately only when nothing
  else in it can proceed. Asking one question at a time is forbidden: that is what forces the
  human to watch the terminal.
- **Delegation is the default** for design- and implementation-level judgments inside a 委任;
  asking is the exception. A recurring question becomes a 委任 at the next decision sheet.
- **Park, don't stall.** An unresolvable point goes into the task document's 質問キュー and you
  move to the next item.
- **The task document spans the whole work**: created when the work is identified (phase 1, or the
  moment a module's 03-impl is drafted), deleted at the end of phase 3; it carries the closure,
  decision sheet, 未決点, 調査メモ, 質問キュー, DoD, and 進捗メモ, so any phase resumes exactly
  after `/clear`. Its `phase:` field says whether the work is queued (`ドキュメント`) or being
  implemented (`実装`).
- **Unit of a work (= one task document) = what implementation can finish and verify in one go:**
  a change set → ONE work spanning every module its closure touches (slug = the change slug); a
  greenfield build → ONE work PER MODULE (slug = `initial-<module>`, plus `initial-e2e`). Note the
  document phase batches by LAYER while a work is a change set or a module — the two units are
  deliberately different, so one `/gen` run over a layer yields several works. Never split a work
  to make it smaller: if it cannot be finished in one go, the module is too big and the 分割定義 in
  02 is the thing to revise (/change, origin design). Trivial fixes under the Exceptions section
  need no task document at all.
- One work = one closure; one change reason = one history entry. Finding mid-phase that the
  closure was too small is normal: extend it and stay in the phase — never leave and re-enter.

## Workflow rules (YOU MUST)

1. **Before implementing or changing anything, read the target module's 03-impl and the
   full document chain reached via its `source`.**
2. **Never add features, requirements, design, or modules not present upstream.**
   On ambiguity, contradiction, or a gap, never assume — but do not stall the phase either.
   Classify the point and keep working:
   - **Inside a 委任 entry's guardrails → decide autonomously** (the default for design- and
     implementation-level judgments). Record the decision where it belongs (the document being
     written, or 「実装上の判断」 in 03-impl) **always citing its D-n**, and append a 委任判断
     entry to the feedback log at the same moment — both records are mandatory (doc = what was
     decided, for this project; log = the delegation was exercised, for the upstream kit;
     /doc-check cross-checks them via the D-n).
   - **A 要確認 entry, a conflict with request.md's 「やらないこと」, or a judgment that changes
     the meaning of a requirement outside every 委任範囲 → you may NEVER decide these yourself.**
     Park the point in the task document's 質問キュー, proceed with everything that does not depend
     on it, and surface all parked points together on the phase's decision sheet. Halt the phase
     outright only when nothing else in it can proceed.
   Never stretch a 委任範囲 by interpretation.
3. **Changes flow from the origin layer downward.** Never patch only downstream or code.
   Origin: purpose/scope changes → 00 / behavior changes → 01 /
   structure or module split changes → 02 / implementation detail only → 03.
   **Requirements are a living document — never assume they are perfectly fixed.** Any
   judgment that changes or fills a REQUIREMENT — even one made downstream or during
   implementation, by human OR AI (resolving an ambiguity, exercising a 委任, discovering a
   gap while coding) — has 00 as its origin: **reflect it back into `00-requests/` (usually
   decisions.md), then flow it downward** — via /change when the work has not started, or as part
   of the current phase's descent (with the decision sheet's agreement) when it has. Recording it
   only in a
   downstream doc (01/02/03 「実装上の判断」) or the feedback log is NOT sufficient when the
   judgment is requirement-level: 00-requests must always describe the current truth. Judge
   scope honestly — a pure implementation detail stays in 03, but when in doubt whether a
   decision touches requirements, route it up to 00. This applies through the implementation
   phase, not just requirements/design.
   **Flowing from the origin happens INSIDE the current phase.** Discovering while verifying 03
   that the real origin is 01 does not end the phase and does not hand off to another skill: pull
   00/01/02 into the closure and fix them in this phase's single top-down descent (00-layer edits
   still need human agreement — collect them onto the decision sheet rather than asking one by
   one). Leaving the phase to re-enter it from the top is the round trip this system forbids.
4. **Human review is optional.** The quality gate is verification by /doc-check; the human
   looks only when they want to, and may order fixes or re-verification.
5. **Implement only after the task document exists and its 未決点 list is empty**; per task,
   update checkboxes, commit, and update 進捗メモ. On completion, verify the DoD item by item,
   sync the module's 03-impl to the real implementation, **confirm every 質問/修正/委任判断 that
   occurred in this work has its feedback-log entry** (append any missing ones now — late beats
   lost), then delete the task file through the gate (principle 5).

## Knowledge capture (docs/knowledge/)

1. **When the human overrides, rejects, or reverses something the AI proposed and no
   reason is given, ask why** before moving on — one focused question to capture the
   rationale. The human's decision stands regardless of the answer: asking is for
   learning, never for renegotiating.
2. **Record each insight so gained as ONE Japanese file per insight** in
   `docs/knowledge/<slug>.md` (kebab-case slug). Contents: the situation, the AI's
   proposal, the human's decision and stated reason, and the generalized lesson
   (今後どう活かすか). Other non-obvious lessons learned during work may be recorded
   the same way. Never bundle distinct insights into one file.
3. `docs/knowledge/` is NOT a specification document: no version/verified, outside
   /doc-check, never a source of requirements or design. Before proposing in an area,
   scan the file names under `docs/knowledge/` and read only the relevant entries.
   When the same insight deepens later, update its file in place.

## Feedback log (docs/feedback/log.md) — telemetry for the upstream kit

The upstream requirements kit improves by measuring what THIS project had to ask. Maintain
ONE append-only file `docs/feedback/log.md` (create on first entry). Append an entry, at
the moment it happens, whenever:

1. **質問** — you had to ask the human (on a decision sheet) because the specification documents
   are ambiguous, contradictory, or incomplete — one entry per question, logged when it is
   answered (spec-content questions only; not tool/env trouble).
2. **修正** — the human corrects delivered output (documents or behavior) and the root
   cause traces to the requirements package (missing/wrong/ambiguous in 00-requests/).
3. **委任判断** — you exercise a 委任 from decisions.md (cite its D-n).

Entry format (Japanese, a few lines each):

```markdown
### [連番] YYYY-MM-DD 種別: 質問|修正|委任判断
- 作業文脈: (どの層のどの作業中か)
- 内容: (聞いたこと+回答 / 指摘と修正 / 下した判断+D-n)
- 根本原因: (00-requests/ のどのファイルに何が書いてあれば防げたか。委任判断なら「なし」)
```

Rules: NOT a specification document (no version/verified, outside /doc-check); never a
source of requirements or design; never write tasks here. Distinct from docs/knowledge/
(insights for THIS project) — the feedback log is raw telemetry consumed by the upstream
kit's /feedback, which appends `[還元済 日付]` marks. Do not edit past entries otherwise.
When unsure whether something qualifies (was that a 委任判断? does the correction trace to
00?), log it anyway — over-logging is harmless, missing telemetry is not. Enforcement:
/gen reports exercised 委任判断 after generating, /implement audits the log at completion
(task DoD includes it), and /doc-check cross-checks D-n citations against log entries.

## External-agent delegation (Codex) — independent audit and independent QA

Part of the quality gate is delegated to an INDEPENDENT agent — for review independence (Claude
auditing its own output carries its own assumptions) and load balancing: document auditing and
the 実装可能性 dry-run inside `/doc-check`, and QA (E2E execution, failure investigation,
exploratory browser testing) after implementation. Procedures: `/codex-audit` (modes `docs` /
`diff` / `readiness`), `/codex-qa`.
The invariants below are the policy; the procedures, the execution environment, and the staged
rollout (which phase gates what) live in `/codex-audit` §6–§7. Project settings (enabled?, command,
profiles, timeouts, CDP endpoint, seed/reset commands, artifact directory, rollout phase):
「Codex実行設定」 in `docs/_steering/tech.md`. Codex's own standing constraints: `AGENTS.md`.

Invariants (never bend these, whoever invokes the skill):

1. Claude Code remains the sole owner of process, decisions, and writes — and **「Claude Code」 means
   the main session AND any subagent it spawns to EXECUTE a Claude skill**: a `/doc-check` launched
   as a fresh-context subagent IS that skill's run, so it edits documents, appends histories, and
   writes `verified` exactly as the main session would. A subagent in the **independent-lens role**
   (invariant 7) is a different role entirely and writes nothing. Codex NEVER writes specification
   documents, code, histories, the feedback log, or `verified`, never decides an open spec question,
   is never a second `/doc-check`, and is never a `source` of any document.
2. Codex output is EVIDENCE, not a verdict. Claude adjudicates every finding as
   確認済み・自動修正可能 / 確認済み・人間判断が必要 / 誤検知(concrete reason required) /
   判定不能(→ 人間判断が必要). Never auto-apply a Codex suggestion.
3. An unresolved severity-高 finding blocks PASS and blocks work completion. Silently ignoring one
   is forbidden; dismissals are reported with their reason. **Sole exception, wherever the finding
   comes from (you or the independent lens): the A3 「未検証(テスト未実装)」 class** — a test table row
   with no test yet. It is severity-高 so it can never be silent, but it does not block PASS, because
   a 03-impl written before its code necessarily has such rows; the work's DoD is what closes them.
   No other exception exists, and a rollout phase cannot create one (`/codex-audit` §7).
4. Independence: hand Codex only target / scope / criteria / output format — never your own
   findings, fix plan, or expected verdict.
5. Document auditing is strictly read-only (`--sandbox read-only --ephemeral`, no network).
   QA is NOT read-only — it mutates application state: dedicated seed, exclusive browser access
   (Claude / Codex / Playwright / human never concurrently), reset afterwards, and only test
   artifacts may be written. Never use approval- or sandbox-bypassing flags, never embed secrets
   in a prompt, never execute Codex output as a command.
6. Codex being unavailable or failing is a TOOL problem: record it in the report, never in
   `docs/feedback/log.md` (a 質問 raised to the human *because of* a Codex finding is logged as
   usual). Fail-open/closed policy per caller lives in `/codex-audit`.
7. **Fallback: never leave the independent lens empty.** Codex unavailable or failing → delegate
   the same request to a **fresh-context Claude Code subagent** under identical constraints (same
   target/scope/criteria/format, none of your findings, read-only for audit and dry-run).
   Independence is weaker (shared blind spots) but a fresh context cannot be anchored by reasoning
   it never saw. This invariant governs the LENS role only: it never restricts a subagent that IS a
   skill's own run (invariant 1). Always state WHICH lens ran (Codex / subagent / なし); a subagent run never
   passes as a Codex audit. A successful fallback lifts the `audit_failed` PASS block for
   incremental and `<module-slug>` runs only — `full` and milestone runs still need Codex or an
   explicit human decision.

## Document locations

- Shared premises (always in effect): @docs/_steering/product.md, @docs/_steering/tech.md, @docs/_steering/structure.md
  These are @-imported into EVERY session (context cost is permanent): keep them lean —
  only premises needed in every session. Situational detail belongs in 02-design / 03-impl.
  When proposing steering additions, apply this test first.
  **Before `/setup` these three files do not exist yet** (the kit ships only their templates in
  `docs/_templates/_steering/`). While they are absent, never guess what they would say: any rule
  that reads them — exact lint/test commands, 「Codex実行設定」, naming conventions — stops and points
  to `/setup` instead. Their heading structure is fixed; skills look sections up by name.
- Specification documents (SSOT): 00–03 directly under `docs/` (structure per principle 2;
  the 00 layer is the `docs/00-requests/` package)
- Change history: `docs/histories/YYYY-MM-DD-<slug>.md`
- Working tasks: `docs/tasks/<work-slug>.md` (exists only while in flight)
- Insights: `docs/knowledge/<slug>.md` — lessons captured from human decisions
  (one file per insight; see the Knowledge capture section)
- Telemetry: `docs/feedback/log.md` — 質問/修正/委任判断 entries for the upstream kit
  (see the Feedback log section)
- Templates: `docs/_templates/` (ALWAYS consult when generating or updating) — the 4 layers,
  history, task, and `_steering/` (product/tech/structure, instantiated by `/setup`)
- Codex delegation: policy = the External-agent delegation section of THIS file; procedure,
  execution environment, and rollout phases = `/codex-audit` §6–§7 and `/codex-qa`; Codex's own
  standing constraints = `AGENTS.md`; project settings = 「Codex実行設定」 in
  `docs/_steering/tech.md`
- `INDEX.md` at the project root (a project convention): a list of every project-related
  document with its path and a summary. **When searching for information or locating a
  document, consult INDEX.md FIRST** as the cheapest map, instead of scanning directories.
  However, it may be missing or out of date: treat it as a hint, not truth — verify that a
  listed path exists before relying on it, fall back to normal exploration (frontmatter
  scan, directory listing) when it is absent or inconsistent, and in that case you may
  point out the staleness and propose an update.
- Generic/specific boundary: CLAUDE.md, _templates, skills, and the guides are generic
  (kit-managed); everything else is project-specific. **Project-specific conventions go in
  steering; never modify templates or skills for one project.**
- Human-facing guides (AI normally does not load): `docs/ONBOARDING.md` (intro) /
  `docs/WORKFLOW-GUIDE.md` (operations) / `docs/RATIONALE.md` (rationale). The norms are THIS file,
  the skills, and the templates; on any conflict, the norms win.

## Workflow (skills)

| Skill | Role |
|---|---|
| `/setup` | Interactive project setup; answers fill in steering/ |
| `/gen` | Generate the next specification LAYER in one pass (all files of it), with the 実装ドライラン; no per-file human gate |
| `/change <description>` | **Phase 1 (決定)**: fix the closure, put every question of the work on ONE decision sheet, register 委任, create the task doc, then edit the closure top-down |
| `/implement` | **Phase 3**: gate on 未決点ゼロ, then implement unattended, parking questions instead of stopping |
| `/doc-check [module\|full]` | **Phase 2's closing act**: one converging fix→certify run over the closure (fix at the origin layer, delta verification, certify last); the sole writer of `verified` |
| `/doc-status` | Show derived verification state of all docs and in-flight tasks |
| `/reverse-doc <module>` | Reverse-generate specs from existing code (brownfield adoption) |
| `/estimate-fp` | Compute function points from the specs and report (never written into documents) |
| `/codex-audit [docs\|diff\|readiness] <target>` | Run the independent audit (read-only) and return findings as evidence — `readiness` = the 実装ドライラン lens; falls back to a fresh-context subagent when Codex is unavailable; no adjudication, no fixes, no `verified` |
| `/codex-qa [target]` | Independent QA: run E2E → adaptive failure investigation → CDP exploratory browser testing (subagent fallback); returns evidence, fixes nothing |

Any skill may be invoked by the AI as well as the human. However, the gates inside each
skill (verified checks, obtaining human agreement, stop conditions) must NEVER be skipped,
regardless of who invoked it.

## Writing conventions (all documents)

- Format: Markdown + YAML frontmatter. Never alter a template's heading structure.
- Ambiguous wording is banned (「適切に」「正しく」「高速に」「柔軟に」 etc.); write numbers,
  conditions, and concrete examples.
- Functional acceptance criteria use EARS (WHEN / IF...THEN / WHILE / WHERE + SHALL).
- Diagrams in Mermaid. Target ≤ ~4,000 words per file. When exceeded: split 01 by business
  domain; extract 02 detail designs. **A bloated 03-impl signals an oversized module**:
  never split 03 on your own — propose revising the 分割定義 (/change, origin design).
- Language: user-facing output all in Japanese (see top). Skill bodies (SKILL.md) are
  written in English for token efficiency, keeping output-format skeletons, quoted document
  headings, and verbatim fixed phrases in Japanese.
- UI: screen structure, transitions, items, and states are governed by the UI設計 section of
  02-design (mandatory; state 「UIなし(理由)」 if no UI). Pixel-level appearance is NOT
  specified in documents — follow steering's design principles/tokens at implementation time.

## Verification and completion

- Completion is judged by the task document's Definition of Done. A passing build is NOT
  completion: lint → unit/integration tests → acceptance-criteria tests → affected E2E
  scenarios (per 02's E2Eシナリオ一覧; state 「対象外(理由)」 when none) → 03-impl sync →
  history record, all achieved. The E2E step runs through `/codex-qa` when QA delegation is
  enabled (subagent fallback per invariant 7) — Claude runs it itself only when neither lens is
  available, never skipping it.
- The whole work closes with ONE re-certification run, not one per document: phase 3 syncs every
  03-impl it touched, then `/doc-check` certifies that closure in a single converging run.
- Use the exact test/lint commands from @docs/_steering/tech.md (commands are recorded per
  test level: unit/integration and E2E).

## Context management

- You may suggest `/clear` at task boundaries (progress persists in the task document;
  ALWAYS update 進捗メモ before clearing).
- Do not load specification documents / histories / tasks unrelated to the current work
  (judge relevance from frontmatter `source` / `depends_on` / `summary`).

## Exceptions (when the spec process may be skipped)

- Obvious bug fixes (a few lines), typos, dependency bumps, comment fixes — but NOT if the
  fix contradicts what 03-impl says.
- **What the exception waives is the DOCUMENT process only**: no task document, no closure, no
  decision sheet, no `/doc-check` run. **What never lapses**: lint and the unit/integration tests
  from tech.md must pass, and code ⇄ 03-impl consistency (principle 6) must still hold afterwards.
- **It is NOT an exception** — run the normal phases — when the change could alter observable
  behavior or an interface, when it makes any statement in 03-impl stale (a dependency bump that
  changes an API, a default, or generated output qualifies), or when it touches a module whose work
  is in flight.
- When unsure, ask the human: "does this change affect the specification documents?"

<!-- claude-dev-auto-start -->

## 注意事項

- 必ず公式の最新情報、最新仕様を調べて、それを適用すること

## Web アプリの動作確認（重要）

- コンテナ内で Google Chrome が動作している。ユーザーは noVNC 経由でブラウザ画面をリアルタイムに確認できる
- chrome-devtools MCP サーバー経由で Chrome を操作すること
- **ヘッドレスブラウザを別途起動しないこと**（`chromium.launch()` 等は禁止）

### 動作確認の手順

1. 開発サーバーを起動する（`0.0.0.0` にバインドすること）
2. chrome-devtools MCP で Chrome を操作する（ページ遷移、クリック、入力、スクリーンショット等）
3. ユーザーは noVNC 画面で操作をリアルタイムに確認できる

### 注意事項
- 開発サーバーは `0.0.0.0` にバインドする（`--host 0.0.0.0` 等）
- コンテナ内の Chrome からは `localhost` で開発サーバーにアクセスできる

## Docker ネットワーク（重要）

- このシェルは Docker コンテナ `claude-dev-env` 内で動作している
- `localhost` / `127.0.0.1` では他のコンテナにアクセスできない。必ず**コンテナ名**を使うこと
  - 例: `curl http://localhost:8000` → `curl http://claude-dev-env:8000`
- 自コンテナ内のサーバーへのアクセスは `localhost` で可
- `docker ps` でコンテナ名を確認できる
- 全コンテナは Docker ネットワーク `claude-dev-net` に接続されている

<!-- claude-dev-auto-end -->
