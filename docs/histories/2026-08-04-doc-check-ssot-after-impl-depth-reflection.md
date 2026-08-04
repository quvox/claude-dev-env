---
id: 2026-08-04-doc-check-ssot-after-impl-depth-reflection
date: 2026-08-04
task: task-impl-depth
origin_layer: 03
issue: docs/issues/035, docs/issues/037, docs/issues/038, docs/issues/039, docs/issues/040
summary: task-impl-depth の SSOT 反映後に /doc-check ssot を実行。scope.md だけ再認証し、未解決の重大度「高」3件により 01 の2ファイルの合格証を取り消した
---

<!-- タスクごとに1ファイル。追記のみ(確定したエントリの文章は書き換えない)。
     タスク・進捗・TODO は書かない(それは memo.md の仕事だった)。 -->

# 2026-08-04 task-impl-depth 反映後の SSOT 検証と合格証の更新

## 変更理由

`task-impl-depth` の `/task-close` が変更指示 39 件を SSOT へ反映した(全件 `reflected:` 済み)。
反映により `functional.md` / `usecases.md` / `non-functional.md` などが MINOR bump したため、
それらを `source` に持つ 48 件の合格証が MAJOR.MINOR 不一致で失効した。
`/doc-check ssot task-impl-depth` を実行して再認証を試みた。

起点層は 03(タスクの目的が 03-impl の深度)だが、検証の結果、
**未解決の指摘の起点は 00(`D0-orch-15`)と 01(`NFR-perf-03`)に遡る**ことが判明した。

## 変更内容の要約

- **独立監査を規範の既定(`gpt-5.6-terra` / reasoning `max`)で 7 本走らせた**(成功6 / タイムアウト1)。
  レンズは `docs`(00+01 / 01→02 / 02→03)と `relations`(cli 7本 / orchestrator 7本 × 2)。
  **6本すべてが `verdict: fail`。`git status` は前後で不変(mutation なし)。**
- **未解決の重大度「高」3系統**が確定し、いずれも人間の裁定を要する(委任範囲外):
  1. `NFR-perf-03` 第2文 ⇄ 実装(上限の検出も切り詰めも無い)= `issue 035`
  2. `D0-orch-15`(スキーマ強制)⇄ `FR-orch-06` 受入基準3(スキーマ強制しない)= `issue 039`
  3. 影響範囲内の relations 21本にコードとの乖離 約34件(うち高5件)= `issue 038`
- **`docs/00-requests/decisions/scope.md` のみ再認証**(1.1.0)。
- **`decisions/orch.md` / `functional.md` / `non-functional.md` の合格証を取り消し**、
  取り消しの理由をフロントマター直後のコメントに明記した。
- 機械検査は全合格(`build-callgraphs --check` 最新 / `cluster-features --check` 最新 /
  `callgraph-check` **高0**・中3・低17・参考20 / `check-relations` 合格 82/82 /
  `check-contracts` 合格 / `build-index --check` 差分なし)。
  受入基準カバレッジは **180 = 180**(欠落0・余剰0・重複0)。**コード差分は空。**

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/00-requests/decisions/scope.md | 1.1.0(変更なし) | 合格証を 1.0.0 → **1.1.0 で再発行**。本文は触っていない |
| docs/00-requests/decisions/orch.md | 1.1.0(変更なし) | **合格証を削除**。`D0-orch-15` が `FR-orch-06` 受入基準3 と矛盾(`issue 039`)。取り消し理由をコメントで明記 |
| docs/01-requirements/functional.md | 1.1.0(変更なし) | **合格証を削除**。同上(起点は 00)。あわせて残る「中」3件をコメントに列挙 |
| docs/01-requirements/non-functional.md | 1.1.0(変更なし) | **合格証を削除**。`NFR-perf-03` 第2文が実装と食い違う(`issue 035`)。この1件が 02/03 のほぼ全ドキュメントを「上流未検証」にしている旨も明記 |
| docs/03-impl/index.md | 1.2.0 → **1.3.0** | 「実装の欠陥として起票済み」を 15件 → **17件**(`001` / `002` / **`036`(高・データ破壊)** の漏れを補い、`014` は「既知の制限から参照されていない」ことを明記して数え方の規則を書いた)/「コードとの乖離として未解決のもの」に **`issue 038` の約34件**を追加 /「02 との差分」に **`NFR-perf-03` ⇄ 実装の 01⇄03 差異**を追加して 5件 → **6件** / 合格証を書けない理由を最新の2つ(`issue 038` と上流未検証)へ差し替え |
| docs/03-impl/tests/index.md ほか index 群 | 生成物 | `build-index.py` で再生成(issue 36 → 39 件) |

## 実装したもの

なし。**コードは1行も変更していない**(`git diff --stat -- . ':!docs'` が空)。

## 機能間連携仕様書の変化

なし(本実行は `03-impl/relations/` の本文を書き換えていない。乖離は `issue 038` に記録し、
どちらが正かの判定は人間へ回した — CLAUDE.md 原則2)。

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 新規 issue | docs/issues/038-modify-closure-relations-still-diverge-from-code.md | **severity 高**。影響範囲内の relations 21本が反映後もコードと約34箇所で食い違う(高5件はコードで裏取り)。乖離は変更指示の `sections` に入っていなかった節に集中 |
| 新規 issue | docs/issues/039-modify-00-decisions-not-updated-with-01-refinements.md | **severity 高**。「実装が正」として 01 を精密化した2箇所で 00 の決定事項が追随しておらず、要件が決定に反している(`D0-orch-15` / `D0-sec-10`) |
| 新規 issue | docs/issues/040-modify-architecture-contradicts-itself-on-credential-copy-target.md | severity 中。`architecture.md` が認証ファイルのコピー先を「プロジェクトディレクトリ配下」と「コンテナローカル」の2通りに書いており、上流 `FR-env-03` 受入基準2 と片方が食い違う |
| 追記 | docs/issues/037-modify-pull-partial-success-and-untested-retag.md | ② の前提が成立しないことをコードで確認して追記(`docker tag` は `set -e` で非0終了するので `FR-env-09` 受入基準11 は満たされている)。**2026-08-04 の裁定は再検討が必要** |
| 重大度の是正 | docs/issues/032-...(高 → 中) | 高2件(state-intervention / streamlog)が反映で解消したことをコードで確認し、該当行に「解消済み」印を付けて severity を中へ下げた |
| 追記 | docs/issues/017-modify-residual-unmeasurable-words-in-relations.md | 測定不能語を2箇所追加(`02-design/relations.md:91`「高速更新」= 2レンズが独立に検出 / `02-design/logging.md:69`「必要な範囲を超えて出さない」)。私の走査語が `高速に` だけで `高速更新` を取りこぼした事実も記録 |
| 解消した issue | なし | `008` / `016` / `018` / `034` は DoD で削除予定だが**まだ `docs/issues/` に存在する**(`/task-close` の未了ステップ)。`034` は `issue 039` により実質未解消 |

---

# 2026-08-04(2回目)新しい実行の `/doc-check ssot task-impl-depth`

## 変更理由

上の実行が残した未解決の重大度「高」3系統(`issue 035` / `039` / `038`)のうち、
`035` と `039` は人間の裁定を受けて SSOT が修正された(`decisions/orch.md` 1.2.0 /
`decisions/sec.md` 1.1.0 / `non-functional.md` 1.2.0 /
`02-design/contracts/orchestrator-prompt.md` 1.2.0 / `03-impl/index.md` 1.4.0)。
**意味のある修正が入った以上、監査した状態と合格証を受ける状態が違う**ため、
`/doc-check ssot task-impl-depth` を新しい実行として走らせ、独立監査を掛け直した。

## 変更内容の要約

- **独立監査を Codex 5本で実施(全部成功)**。`gpt-5.6-terra` / reasoning `max`、
  `--sandbox read-only --ephemeral`、`-c features.use_legacy_landlock=true`。
  レンズは `docs`(00+01 の A0/A1)/ `docs`(01→02 の A1/A2)/ `docs`(A3 テスト対応表)/
  `readiness`(03 契約。**コードを1件も読んでいない**)/ `docs`(E: PLAN ⇄ MODULE、86ファイル読取)。
  **5本すべて `verdict: fail`。`git status` は前後で不変(mutation なし)。**
  前回 880 秒でタイムアウトした問題は、スコープを5本に細かく割ることで再発しなかった。
- **`issue 039` と `issue 035` の解消を確認**した。独立レンズも
  「現行 `D0-orch-15` と `FR-orch-06` #3/#6/#7 は両立している」と独立に確認している。
- **新しい未解決の重大度「高」1件を確定させた** = `issue 040` を**中 → 高**へ是正。
  独立レンズは `architecture.md` の自己矛盾として挙げただけだが、Claude がコードまで辿り、
  **起点が 00 の `D0-auth-03`** であること、**実装はプロジェクトディレクトリ配下 + symlink**
  であること、**03-impl は実装を正確に記述している**ことを確定させた。
- **合格証を3件発行、9件を取り消した**(下表)。
- **自動修正1件**: `FR-env-08` 受入基準5 に `--vm-fresh` を追加(A1 のカバレッジ欠落)。
- 機械検査は全合格で前回と同値(`callgraph-check` **高0**・中3・低17・参考20 /
  `check-relations` 82/82 合格 / `check-contracts` 合格 / 受入基準カバレッジ **180 = 180**)。
  **コードは1行も変更していない**(`git diff --stat -- . ':!docs'` が空)。

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/00-requests/decisions/orch.md | 1.2.0(変更なし) | **合格証を 1.2.0 で再発行**。`issue 039` の解消を認証。本文は触っていない |
| docs/00-requests/decisions/sec.md | 1.1.0(変更なし) | **合格証を 1.0.1 → 1.1.0 で再発行**。`D0-sec-10` の VM/KVM 追記を認証 |
| docs/01-requirements/non-functional.md | 1.2.0(変更なし) | **合格証を 1.2.0 で発行**。`issue 035` の解消を認証。残る「中」5件・「低」2件を `issue 043` としてコメントに明記 |
| docs/01-requirements/functional.md | 1.1.0 → **1.2.0** | `FR-env-08` 受入基準5 に `--vm-fresh` を追加。冒頭コメントを差し替え(`issue 039` 解消 → `issue 040` が新たな阻害要因)。**合格証は書けない** |
| docs/00-requests/decisions/auth.md | 1.0.0(変更なし) | **合格証を削除**。`D0-auth-03` / `D0-auth-02` が実装と食い違う(`issue 040`)。取り消し理由をコメントに明記 |
| docs/02-design/architecture.md | 1.0.0(変更なし) | **合格証を削除**。認証コピー先の自己矛盾(`:84`〜`:86` が正、`:142` が誤り)。起点が 00 なので `:142` だけの自動修正は行わなかった |
| docs/02-design/environments.md ほか7件 | 変更なし | **合格証を削除**(上流未検証の連鎖)。`infra/local/docker-resources.md` / `02-design/contracts/docker-api.md` / `02-design/contracts/entrypoint-firewall.md` / `03-impl/contracts/docker-api.md` / `03-impl/contracts/entrypoint-firewall.md` / `03-impl/environments/images.md` |
| docs/issues/index.md | 生成物 | `build-index.py` で再生成(39 → 42 件) |

**合格証が有効な文書は 10 件**になり、**「上流未検証なのに合格証が残る文書」は 0 件**になった。

## 実装したもの

なし。**コードは1行も変更していない。**

## 機能間連携仕様書の変化

なし(`03-impl/relations/` の本文を書き換えていない)。
**E(02 ⇄ 03 連携差分)は合格**: PLAN 63 / MODULE 82 で、PLAN のみ 0 件、MODULE のみ 19 件
(orchestrator 内部18本 + mathkit)。これは `02-design/relations.md:27`〜`:30`, `:102` が
意図的除外として明記しているものと完全に一致し、共通 63 件で `callees` 差異 0・`contracts` 差異 0。
**Claude の機械照合と独立レンズ(86ファイル読取)が独立に同じ結論に達した。**

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 重大度の是正 | docs/issues/040(中 → **高**) | 認証ファイルのコピー先と symlink。コードで論点を確定させ、起点が 00 の `D0-auth-03` であることを特定。対処案 B が採れないことも記録 |
| 新規 issue | docs/issues/041 | **中**。「ブロック対象ドメイン」の集合が 00/01 のどこにも無い。`D0-sec-04` は「表現方法」だけを委任している。**前回の実行の棄却理由が成立しないことを確認** |
| 新規 issue | docs/issues/042 | 中。`AC-02`「ポート非公開」が `AC-01`(noVNC URL 表示)と `D0-env-01`(6080 番台動的割当)と両立しない(00 層の A0 不整合) |
| 新規 issue | docs/issues/043 | 中。NFR 5件で目標値・測定方法が要件本文の一部しか測っていない。曖昧語が無いため C7 では検出されず、**4列の対応を突き合わせないと見えない**種類の欠落 |
| 追記 | docs/issues/005 | 独立レンズ2本が「高」と評価したが**中に留めた**。理由 = `D0-sec-05` の委任範囲が「解釈できない入力を通すか止めるか」を明示的に含む。ただし残存リスクが `既知の制限` でなく `実装上の判断` に書かれている不備を新たに特定 |
| 追記 | docs/issues/028 | `03-impl/contracts/cli-container.md` の `## 設計との差異` が「差異なし」と誤記(本文は別パス同名を同一セッションと明記している) |
| 追記 | docs/issues/038 | 次タスクの影響範囲に3件追加(02契約「必須」⇄ 03「ゼロ値」/ `MODULE-orchestrator-review` に `issue 034` の「要確認」が裁定後も残存 / 21本の MODULE ID 未列挙) |
| 追記 | docs/issues/017 | 測定不能語2箇所(`FR-env-08` #4「資源逼迫」/ `FR-orch-02` #3「必要な文脈だけ」)。**2本のレンズが独立に検出し、Claude の走査語には無かった** |

## キット側に残した欠落(`/kit-improve` 案件)

1. **合格証の検査が version 一致だけで、「上流が version を変えずに合格証を失った」ことを
   表現できない。** 本実行で `02-design/contracts/docker-api.md` /
   `entrypoint-firewall.md` の2件が、**上流未検証のまま機械的な検査を通り抜けていた**ことが
   判明した(= `close-task.py` のゲート(b) を誤って通りうる)。合格証の検査に
   「`source` が現に合格証を持つか」を加える必要がある。
2. **禁止語の走査を人が手で組むと検索語の設計次第で取りこぼす。** 本実行では
   「資源逼迫」「必要な文脈だけ」を Claude が取りこぼし、独立レンズが拾った。
   CLAUDE.md §8 の禁止語一覧を単一の正本として持つ検査スクリプトが必要(`issue 017` 対処案 B)。
3. **`| ID | 要件 | 目標値 | 測定方法 |` の4列の対応を検査する仕組みが無い**(`issue 043` 対処案 C)。
   曖昧語が無くても「要件の一部しか測っていない」欠落は残る。
4. **`.claude/skills/codex-audit/audit-schema.json` を `--output-schema` に渡すと HTTP 400**
   (既知)。本実行もスキーマ相当の JSON 形をプロンプト本文へ埋めて回避した。
5. **独立監査のスコープを狭く割るほど誤検知が増える**という取引が観測された。本実行の
   誤検知7件のうち3件(受入基準 74/180、E2E-03・06 不在、index.md の 17件リスト)は
   **私が渡した読み取り範囲が狭すぎたことによる人工物**である。範囲を割るときは
   「その検査項目が成立する最小の集合」を外さないこと(A3 のカバレッジ検査は `tests/` 全件、
   SR-* を含む A2 は `01-requirements/system.md` が必須)。
