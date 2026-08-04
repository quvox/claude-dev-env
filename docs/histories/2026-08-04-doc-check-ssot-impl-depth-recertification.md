---
id: 2026-08-04-doc-check-ssot-impl-depth-recertification
date: 2026-08-04
task: task-impl-depth
origin_layer: 00
issue: docs/issues/017, docs/issues/019, docs/issues/028, docs/issues/034, docs/issues/038, docs/issues/040
summary: task-impl-depth 反映後の SSOT を全面再認証した。issue 040 の裁定が 00 の委任ガードレールまで降りていなかった矛盾を解消し、issue 038 の「高」5件の解消をコードで確認して重大度を高→中に是正した結果、版を持つ仕様ドキュメント 64 件すべてに有効な合格証が揃った
---

<!-- タスクごとに1ファイル。追記のみ(確定したエントリの文章は書き換えない)。
     タスク・進捗・TODO は書かない(それは memo.md の仕事だった)。 -->

# 2026-08-04 task-impl-depth 反映後の SSOT 全面再認証

## 変更理由

`/doc-check ssot task-impl-depth` を新しい実行として走らせた。直前の実行が
「未解決の重大度『高』3系統」により合格証を3件しか出せず、**02・03 のほぼ全ドキュメントが
「上流未検証」のまま**残っていたため、`close-task.py` のゲート (b) が通らない状態だった。

本実行で判明したのは、**残っていた「高」2件はいずれも既に人間の裁定を受けており、
その裁定の下降が最後の一歩で止まっていた**ということである。

1. **`docs/issues/040`(認証ファイルの置き場所と symlink)**: 人間が案A(実装が正)で裁定し、
   `D0-auth-03` / `FR-env-03` #2・#7 / `architecture.md` の3層は改まっていた。しかし
   **同じファイルの `D0-auth-02`(委任)のガードレールが「(symlink にしない)」のまま残り、
   改めた `D0-auth-03` と正面から矛盾していた**(check A0)。裁定は `D0-auth-02` も名指しして
   いたのに下降が届いていなかった。
2. **`docs/issues/038`(影響範囲内 relations 21本の乖離)**: 最終的な裁定は**案B**(「高」5件は
   `task-impl-depth` で直し、中低27件は別タスク)で、5件はすべて SSOT へ反映済みだった。
   にもかかわらず `severity: 高` のままだったため、`03-impl/index.md`(relations 層の代表)を
   再認証できない状態が続いていた。

## 変更内容の要約

- **独立監査は1本も成立しなかった。** 規範の既定(`gpt-5.6-terra` / reasoning `max`、
  `--sandbox read-only --ephemeral -c features.use_legacy_landlock=true`)で5本を並列起動したが、
  全本が `ERROR: You've hit your usage limit`(復旧予定 2026-08-10)で終了し成果物を返さなかった。
  環境要因が明らかで、かつ再試行しても同じ結果になるため再試行はしていない。
  CLAUDE.md 不変則7 により**サンドボックス役の代替は無断で立てない**ので、
  本実行は**独立レンズなし**で進めた(`/doc-check` §5 の `ssot` 増分の fail ポリシー = 警告して続行)。
  **したがって本実行が出した合格証は Claude 単独の検証に基づく。**
- **`docs/issues/038` の「高」5件をコードで全件照合し、解消を確認**した(下表)。これを根拠に
  severity を **高 → 中** へ是正した(2026-08-03 に `issue 032` へ行ったのと同じ是正)。

  | # | 反映先 | 突き合わせたコード |
  |---|---|---|
  | 1 | `MODULE-orchestrator-controller.md` の `Run` 引数 | `orchestrator/controller.go:52`(`Run(ctx context.Context) error`) |
  | 2 | 同・状態保存と中断 | `controller.go:70`・`:1080` は `return err` / `:88`〜`:98` は `errSuspended` を吸収して `nil` |
  | 3 | `MODULE-orchestrator-state-intervention.md` の異常系 | `orchestrator/state.go:396`〜`:402`(全エラーで空キュー) |
  | 4 | `MODULE-orchestrator-handoff.md` の引数表 | `orchestrator/handoff.go:49`〜`:52`(`poll <= 0` で 500ms) |
  | 5 | `MODULE-orchestrator-review.md` の検証範囲 | `review.go:296`〜`:312` / `:24`〜`:31`(`severity` 値域は未検証) |

- **`docs/issues/040` の裁定の残りを下降させた**: `D0-auth-02` のガードレールを
  「`D0-auth-03` が定める形から変えない(共有ボリュームから直接 symlink で参照する形にはしない)」へ
  改めた。実装との一致は `claude-dev:690`,`:749`〜`:766`,`:908` と
  `scripts/entrypoint-claude.sh:199`,`:212`〜`:215`,`:226` で再確認した。
- **同じ裁定が届いていなかった 03 の1箇所も直した**:
  `03-impl/infra/local/docker-resources.md` の「シークレットの置き場所」表が
  「起動時にコンテナローカルへコピー」のままで、**コードにも裁定後の 00/01/02 にも反していた**。
- **裁定済みの論点が「要確認」として残っていた2箇所を解消**:
  `MODULE-orchestrator-review.md` の `issue 034` 行(`FR-orch-06` #3 は既に改訂済みで不一致は無い)と、
  `03-impl/contracts/cli-container.md` の `## 設計との差異`「差異なし」(`issue 028` が文面を確定済み)。
- **`03-impl/index.md` に「01(要件)との差異(未解消のもの)」節を新設**した。従来
  「01(要件)との差異は無い」と述べていたが、`issue 028` / `005` / `036` / `038` #3 / `014` が
  それを否定していた(check C12)。
- **`docs/issues/019` の実在しないテスト識別子 8 件のうち 7 件を実名へ置換**した
  (`orchestrator/` と `docker-proxy/` の `func Test…` を機械抽出して照合)。残る
  `TestReadyTasks_Basic` は対応先が一意に決まらないため issue に残した。
- **`docs/issues/017` に測定不能語を 7 箇所追加**した。とくに `資源逼迫` は 01 から 02 の
  5 箇所へそのまま伝播しており、`02-design/logging.md:88` の「検知した指標と閾値」は
  その指標と閾値をどこにも定義していない(D13 相当)。
- **機械検査は全合格**: `build-callgraphs --check` 最新 / `cluster-features --check` 最新 /
  `callgraph-check` **高0**・中3・低17・参考20 / `check-contracts` 合格 /
  `check-relations` 合格(82/82)/ `build-index --check` 差分なし。
  受入基準カバレッジ **180 = 180**(欠落0・余剰0・重複0)、NFR 15/15。E2E-01〜06 全件対応。
  **コード差分は空**(`git diff --stat -- . ':!docs'`)。

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/00-requests/decisions/auth.md | 1.1.0 → **1.2.0** | `D0-auth-02` のガードレールを `D0-auth-03`(改め後)と整合させた。**合格証を再発行** |
| docs/01-requirements/functional.md | 1.3.0 → **1.3.1** | 本文は無変更。先頭コメントが解消済みの「高」を未解決として述べていたので実態へ書き換えた。**合格証を再発行** |
| docs/01-requirements/usecases.md | 1.1.0(変更なし) | **合格証を再発行**(`against` の `functional.md` が古かった) |
| docs/02-design/architecture.md | 1.1.0 → **1.2.0** | `DSN-arch-02` の箇条 2 が認証の実体を「コンテナローカル」と書き、同じ節の表(プロジェクトディレクトリ配下)と矛盾していたので揃えた。**合格証を再発行** |
| docs/02-design/contracts/cli-container.md | 1.1.0 → **1.2.0** | `DSN-auth-01 の適用` の「symlink ではなくコピー」が、ホームからの symlink 参照と並べると誤読を招くため射程を明示した。**合格証を再発行** |
| docs/02-design/{system,relations,logging,environments}.md | 変更なし | **合格証を再発行**(上流の再認証による) |
| docs/02-design/contracts/{cli-orchestrator,orchestrator-prompt,docker-api,entrypoint-firewall}.md | 変更なし | **合格証を再発行** |
| docs/03-impl/contracts/cli-container.md | 1.1.0 → **1.2.0** | `## 設計との差異` の「差異なし」を、名前の一意性が `NFR-scale-01` を満たさない差異として書き直した。**合格証を再発行** |
| docs/03-impl/infra/local/docker-resources.md | 1.0.0 → **1.1.0** | 認証の置き場所をコードと 00/01/02 に揃えた。**合格証を再発行** |
| docs/03-impl/index.md | 1.4.0 → **1.5.0** | 「01(要件)との差異」節を新設 / `issue 038` の残件を「約34件」→「残 27 件(表 #7〜#32)」へ / 機械検査の実施日を更新。**合格証を再発行**(2026-08-03 以来はじめて) |
| docs/03-impl/relations/MODULE-orchestrator-review.md | (層の代表が持つ) | `issue 034` の「正がどちらかは要確認」を削除(裁定済み・不一致は解消) |
| docs/03-impl/tests/orchestrator.md | 1.1.0 → **1.1.1** | 実在しないテスト識別子 7 件を実名へ置換。**合格証を再発行** |
| docs/03-impl/tests/ の他 31 件 / contracts 4 件 / environments/images.md / infra/local/ghcr.md | 変更なし | **合格証を再発行**(上流の再認証による) |

**結果: 版を持つ仕様ドキュメント 64 件すべてに有効な合格証が揃った。**

## 実装したもの

なし。**コードは1行も変更していない**(`git diff --stat -- . ':!docs'` が空)。

## 機能間連携仕様書の変化

`MODULE-orchestrator-review.md` の `## 既知の制限` の1行(裁定済みの論点が「要確認」として
残っていた記述)を訂正した。`callees` / `contracts` / `tests` の構造は変えていないため、
`check-relations.py` と `callgraph-check.py` の結果は変わっていない(82/82 合格、高0)。

**残る乖離は `issue 038` の中低27件と `issue 032` の18件、`issue 009` (a) の17件、
`issue 019` の1件**で、いずれも「コードが正・記述が古い」型として人間が裁定済みであり、
次のタスクで1つの影響範囲として扱う。`03-impl/index.md` はこれを既知の乖離として列挙している。

## この実行が残した限界(必ず申し送る)

- **独立レンズが1本も走っていない。** 修正と再検証を同じセッションで行うのは自己レビューであり、
  それを補償するのが独立レンズなので、**本実行の合格証はその補償を欠いている**。
  Codex の利用上限は 2026-08-10 に復旧する見込みなので、**復旧後に
  `/doc-check full` を新しいセッションで1回走らせること**を強く勧める。
  過去の実行では毎回、独立レンズが Claude 単独では見つけられなかった指摘を出している。
- **`docs/issues/036`(severity 高・データ破壊: `start` の後片付けが同名の稼働中コンテナを消す)は
  開いたまま**である。人間が「本タスクでは閉じる / 次タスクで優先的に修正」と裁定しており、
  `MODULE-cli-start` と `03-impl/index.md` が事実を正確に記述しているため合格証はブロックしていないが、
  **コードの欠陥は残っている**。
