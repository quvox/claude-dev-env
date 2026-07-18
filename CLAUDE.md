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
   ALL of its `source` documents are verified.
4. **`docs/histories/` is the change history of documents** (all specification documents
   plus steering). One entry per change reason (`YYYY-MM-DD-<slug>.md`); record every updated
   document in affected. (No entry for initial 1.0.0 or PATCH-only edits.) Append-only.
   **Never write tasks or progress here.**
5. **`docs/tasks/<work-slug>.md` is the AI's working document.** Exactly two roles:
   (a) persisting progress across sessions, (b) holding the work's Definition of Done.
   Not subject to human approval. **Delete on completion — and also on abort** (git keeps
   the trail; document changes are already in history).
6. **Code ⇄ 03-impl consistency is an invariant.** When you change code, update the module's
   03-impl (and upstream if needed) within the same work. On discovering divergence, report
   it and ask the human which side is correct.

## Workflow rules (YOU MUST)

1. **Before implementing or changing anything, read the target module's 03-impl and the
   full document chain reached via its `source`.**
2. **Never add features, requirements, design, or modules not present upstream.**
   On ambiguity, contradiction, or gaps: do not assume — stop and ask/report.
   **Sole exception — delegation**: if the ambiguous point falls inside a 委任 entry of
   `00-requests/decisions.md`, do NOT ask: decide autonomously within that entry's
   制約(ガードレール), record the decision where it belongs (the document being written, or
   「実装上の判断」 in 03-impl) **always citing its D-n**, and append a 委任判断 entry to
   the feedback log (below) at the same moment — the two records are BOTH mandatory
   (doc = what was decided, for this project; log = the delegation was exercised, for the
   upstream kit; /doc-check cross-checks them via the D-n).
   Never stretch a 委任範囲 by interpretation; outside the stated range, the base rule
   (stop and ask) applies. A 要確認 entry is the opposite: an explicit order to stop there.
3. **Changes flow from the origin layer downward.** Never patch only downstream or code.
   Origin: purpose/scope changes → 00 / behavior changes → 01 /
   structure or module split changes → 02 / implementation detail only → 03.
   **Requirements are a living document — never assume they are perfectly fixed.** Any
   judgment that changes or fills a REQUIREMENT — even one made downstream or during
   implementation, by human OR AI (resolving an ambiguity, exercising a 委任, discovering a
   gap while coding) — has 00 as its origin: **reflect it back into `00-requests/` (usually
   decisions.md) FIRST via /change, then flow it downward.** Recording it only in a
   downstream doc (01/02/03 「実装上の判断」) or the feedback log is NOT sufficient when the
   judgment is requirement-level: 00-requests must always describe the current truth. Judge
   scope honestly — a pure implementation detail stays in 03, but when in doubt whether a
   decision touches requirements, route it up to 00. This applies through the implementation
   phase, not just requirements/design.
4. **Human review is optional.** The quality gate is verification by /doc-check; the human
   looks only when they want to, and may order fixes or re-verification.
5. **Implement only after creating the task document**; per task, update checkboxes, commit,
   and update 進捗メモ. On completion, verify the DoD item by item, sync the module's
   03-impl to the real implementation, **confirm every 質問/修正/委任判断 that occurred in
   this work has its feedback-log entry** (append any missing ones now — late beats lost),
   then delete the task file.

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

1. **質問** — you stop and ask the human because the specification documents are ambiguous,
   contradictory, or incomplete (spec-content questions only; not tool/env trouble).
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

## Document locations

- Shared premises (always in effect): @docs/_steering/product.md, @docs/_steering/tech.md, @docs/_steering/structure.md
  These are @-imported into EVERY session (context cost is permanent): keep them lean —
  only premises needed in every session. Situational detail belongs in 02-design / 03-impl.
  When proposing steering additions, apply this test first.
- Specification documents (SSOT): 00–03 directly under `docs/` (structure per principle 2;
  the 00 layer is the `docs/00-requests/` package)
- Change history: `docs/histories/YYYY-MM-DD-<slug>.md`
- Working tasks: `docs/tasks/<work-slug>.md` (exists only while in flight)
- Insights: `docs/knowledge/<slug>.md` — lessons captured from human decisions
  (one file per insight; see the Knowledge capture section)
- Telemetry: `docs/feedback/log.md` — 質問/修正/委任判断 entries for the upstream kit
  (see the Feedback log section)
- Templates: `docs/_templates/` (ALWAYS consult when generating or updating)
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
| `/gen` | Decide the next specification document to produce; generate or diff-update (stops at verification gates) |
| `/change <description>` | Change intake: decide origin layer and impact, drive updates and the history record |
| `/implement` | Decide the implementation target, create the task doc, implement (explicit argument optional) |
| `/doc-check [module\|full]` | Verify consistency with a bounded check→fix loop (max 10, exits early when clean); write the verified certificate on passing docs (the sole verifier) |
| `/doc-status` | Show derived verification state of all docs and in-flight tasks |
| `/reverse-doc <module>` | Reverse-generate specs from existing code (brownfield adoption) |
| `/estimate-fp` | Compute function points from the specs and report (never written into documents) |

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
  history record, all achieved.
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
- When unsure, ask the human: "does this change affect the specification documents?"
