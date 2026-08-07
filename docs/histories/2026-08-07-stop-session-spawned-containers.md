---
id: 2026-08-07-stop-session-spawned-containers
date: 2026-08-07
task: task-stop-session-spawned-containers
origin_layer: 00
issue: なし(利用者の要望が起点)
summary: セッションのコンテナ内から compose を経由せずに作られたコンテナとネットワークに docker-proxy が所有者ラベルを付け、stop が所有者一致で、reset が所有者を問わず片付けるようにした
---

<!-- タスクごとに1ファイル。追記のみ(確定したエントリの文章は書き換えない)。
     タスク・進捗・TODO は書かない(それは memo.md の仕事だった)。 -->

# 2026-08-07 セッション内から起動されたコンテナの片付け

## 変更理由

`claude-dev stop` が片付ける対象は、本体コンテナ・`fwd-<name>-*`・compose ラベル
`com.docker.compose.project=<一意化名>` を持つコンテナだけだった。**セッションのコンテナ内から
`docker run`(compose を経由しない経路)で作られたコンテナとネットワークはホストに残り続ける。**

起点は **00-requests**(`D0-env-05` 項2)である。同項が「`stop` 時に片付けるもの」の集合を
compose 資源に限っており、**その集合を広げるかどうかは利用者から見える振る舞いの変更**だから、
`D0-scope-02` の委任では扱えない。下流だけ直すと `D0-env-05` 項2 と実装が食い違う(CLAUDE.md 原則3)。

**やらないと決めたもの**: 名前付きボリュームの削除(`D0-env-05` 項2 の「保持する」を維持)/
`logout` への適用 / VM モード(ゲスト内 Docker はホストに現れない)/ ラベル注入より前に作られた
既存資源の遡及的な片付け(識別する印が無い)。

## 変更内容の要約

- **識別の印を新設した**: docker-proxy が `POST /containers/create` と `POST /networks/create` の
  ボディへ `claude-dev.role=spawned` と `claude-dev.owner-project-dir=<呼び出し元の
  claude-dev.project-dir>` を注入する。**拒否判定をすべて通過したあと**に行い、**付与に失敗しても
  作成を拒否しない**(印が無い資源が残るだけで、利用者の操作は妨げない)。
- **`stop` は所有者一致で消す**(`claude-dev.owner-project-dir=<起動ディレクトリ>`)。
  **`reset` は所有者を問わず消す**(`claude-dev.role=spawned`)。`reset` は対象を絞る引数を持たない
  「ホスト全体を初期状態へ戻す」操作であり、所有者で絞ると `stop` と同義になるため。
- **削除は必ず「セッション由来の資源 → 遊休判定」の順**に置いた。逆順だと、自分がこれから消す
  コンテナが `claude-dev-net` に繋がっているせいで「稼働中のコンテナがある」と数え、共有資源を
  残して事実に反する表示を出す。
- **`stop` は削除の失敗を握り、`reset` は握らない**(`D0-env-08` 項5 が `logout` / `reset` を
  対象とし `stop` を例外としている)。
- 02 に **`DSN-env-04`**(セッション由来の資源の識別)を新設し、識別の規則を3つから4つへ増やした。
  **`PLAN-cli-reset` の節も新設した**(`stop` にだけ設計されていた順序制約が `reset` では
  実装にしか無く、02 を読んでも導けない状態だった)。

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/00-requests/decisions/env.md | 1.2.0 → 1.3.0 | `D0-env-05` 項2 の片付け対象をセッション由来の資源へ拡張。**`D0-env-08` 項8 を新設**(`stop` は所有者一致 / `reset` は所有者非依存)。`D0-env-10` のガードレールを「所有者と種別を表す2つのラベル」へ |
| docs/00-requests/terminology.md | 1.2.0 → 1.3.0 | 「セッション由来の資源」「所有者ラベル」の2語を追加 |
| docs/01-requirements/functional.md | 1.9.0 → 1.11.0 | `FR-env-01` に受入基準22〜27(片付けの対象・順序・失敗の扱い・0件時の無表示)、`FR-env-07` に11・12(ラベル注入)。`FR-env-03-5` の `logout` を「停止」→「**削除**」に訂正、`FR-env-01-6` にセッション由来の資源への参照を追加 |
| docs/01-requirements/decisions/split.md | 1.1.1 → 1.2.0 | `D1-split-01` の分割可否の件数を更新 |
| docs/02-design/architecture.md | 1.3.0 → 1.4.0 | `DSN-arch-02` の状態の置き場の表に、docker-proxy が印を付けるセッション由来の資源(名前は利用者が決める)を追加 |
| docs/02-design/contracts/cli-container.md | 1.4.2 → 1.6.0 | 識別の規則に**規則 D**(所有者ラベル)を追加。エラーケースに `stop` / `reset` の失敗の扱いの区別を追加。規則 C に `reset` の順序、規則 D に削除集合の固定 |
| docs/02-design/contracts/docker-api.md | 1.0.0 → 1.1.0 | 所有者ラベルの注入(対象2経路・上書きの扱い・付与できないときの挙動)を追加 |
| docs/02-design/relations.md | 1.4.0 → 1.6.0 | `PLAN-cli-stop` の節を新設、`PLAN-docker-proxy-serve` に注入の期待を追加、**`PLAN-cli-reset` の節を新設** |
| docs/02-design/system.md | 2.5.0 → 2.7.0 | モジュール分割定義とカバレッジ表を更新。SCR-01 に `stop` / `reset` の片付けの状態を追加 |
| docs/02-design/logging.md | 1.3.0 → 1.4.0 | 片付け結果の表示(種別つき1行ずつ・0件時は無表示)を追加 |
| docs/03-impl/relations/MODULE-cli-stop.md | — → 1.x | 手順8(所有者ラベルによる削除)を追加。遊休判定より前に置く理由を「実装上の判断」へ |
| docs/03-impl/relations/MODULE-cli-reset.md | — → 1.x | `claude-dev.role=spawned` の列挙と削除を追加(確認プロンプトに出す・失敗は握らない) |
| docs/03-impl/relations/MODULE-docker-proxy-serve.md | — → 1.x | 注入の手順と異常系。`tests:` を実数 39 本へ |
| docs/03-impl/contracts/cli-container.md | 1.6.0 → 1.7.0 | 管理ラベルの行に2ラベルを追記、削除対象を引く行を新設。**「定義箇所」の行番号を実装後の実測へ** |
| docs/03-impl/contracts/docker-api.md | 1.1.0 → 1.2.0 | 所有者ラベルの注入の実装事実を `docker-proxy/main.go` の行番号つきで追加 |
| docs/03-impl/contracts/entrypoint-firewall.md | 1.0.0 → 1.1.0 | `NET_ADMIN` の定義箇所が本タスク以前から別の行を指していたので実測へ |
| docs/03-impl/tests/cli-stop.md | 1.4.0 → 1.6.0 | 新条項の対応、テスト識別子を E2E の部分手順の粒度へ。「テスト設計の判断」を新設 |
| docs/03-impl/tests/cli-reset.md | 1.3.0 → 1.4.0 | 同上 |
| docs/03-impl/tests/docker-proxy.md | 1.1.0 → 1.3.0 | `FR-env-07-11` / `-12` を `実装済み` に。`MODULE ⇄ テスト`表を 39 本へ |
| docs/03-impl/tests/e2e.md | 1.2.1 → 1.3.0 | E2E-01 手順8-14(7部分手順)・8-15、E2E-03 手順5・6 を新設 |
| docs/03-impl/tests/strategy.md | 1.2.0 → 1.3.0 | 集計の更新 |
| docs/03-impl/infra/local/docker-resources.md | 1.1.0 → 1.2.0 | セッション由来の資源の命名と識別 |
| docs/03-impl/index.md | 1.16.0 → 1.17.0 | 層代表の再認証。起票済みの実装欠陥を 18 → 21 件へ |

## 実装したもの

| 対象 | 内容 | コミット |
|---|---|---|
| MODULE-docker-proxy-serve | 呼び出し元の解決を2値化(`/workspace` のマウント元 + `claude-dev.project-dir`)。`injectOwnerLabels` / `writeBackBody` を切り出し、コンテナ作成とネットワーク作成の両経路から呼ぶ。単体テスト14本 | `a271d83` |
| MODULE-cli-stop / MODULE-cli-reset | `stop` に手順8、`reset` に `claude-dev.role=spawned` の列挙と削除。共有関数 `spawned_resources` を新設。`claude-dev` と `claude-dev-mac` の両方 | `1d912b4` |

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 変更 | MODULE-cli-stop | 手順8 を追加。`callees` に `MODULE-cli-common-spawned-resources` 相当の共有関数。既知の制限に compose 既定ネットワークの削除失敗が表示されない件(`docs/issues/088`) |
| 変更 | MODULE-cli-reset | 所有者非依存の列挙と削除。`docker volume rm -f` だけが存在しない対象に 0 を返すことを判断12 に明記 |
| 変更 | MODULE-docker-proxy-serve | 注入の手順・異常系・`tests:` 39 本。`rewriteBinds` は `HostConfig` が非 nil なら常に呼ばれることを明記 |
| 変更 | MODULE-cli-logout | 既知の制限を2件追加(`docs/issues/089` の誤表示、`docs/issues/090` の孤児資源) |
| 追加(02) | PLAN-cli-reset | 02 に節が無く、`stop` にだけ設計された順序制約が `reset` では実装にしか無かった |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 新規 issue | docs/issues/087 | 所有者ラベルの注入失敗がコンテナ作成経路でログに出ない(ネットワーク経路は出す) |
| 新規 issue | docs/issues/088 | `stop` が compose 既定ネットワークの削除失敗を表示しない |
| 新規 issue | docs/issues/089 | `logout` がセッション由来のコンテナを「管理ラベルを持たない」と誤表示する(02 が名指しで禁じた状態。4つ目の除外が `reset` にしか実装されていない) |
| 新規 issue | docs/issues/090 | `logout` が作る孤児のセッション由来資源の帰結が 00〜03 のどこにも無い。**人間の裁定 A 済み。書く層は 00・01・02・03 の4つ**(案 A は 01 を落としていた) |
| 新規 issue | docs/issues/091 | `D0-env-08` 項8 に「`reset` が所有者を問わない理由」が無い。**人間の裁定 A 済み。書く層は 00 だけ** |
| 新規 issue | docs/issues/092 | docker-proxy を 00・01 は「停止」、実装は `docker rm -f`(削除)。**人間の裁定 A 済み。書く層は 00・01・02・03 + コード**(案 A は 02 を落としていた)。コードを伴うので独立タスク |
| 新規 issue | docs/issues/083 | 要件(01)の条項が下位層 ID と実装ファイル名を名指す(CS18。本タスクが触る3節の11件は移し済み、残 16 件) |
| 新規 issue | docs/issues/084 | `03-impl/tests/` に「テスト設計の判断」が無い(本タスクの5件は解消、残 27 件) |
| 新規 issue | docs/issues/085 | 02-design が実装の細部(シンボル名・実行順序・出力文言)を持つ 11 件 |
| 新規 issue | docs/issues/086 | 00・01 が実装の機構を持つ 59 件(CS18 が見ないパターン。00 にコードの行番号がある5件が最重) |
| 既存 issue の更新 | docs/issues/076 | `close-task.py` も `feature-graph.md` を除外しないことがフェーズ4の実測で判明。`pattern_survey` を 1 件 → 2 件へ訂正 |
| 既存 issue の更新 | docs/issues/078 | frontmatter が YAML として解析できないファイルを再走査。2件 → 5件(いずれも SSOT 外) |
| 棚上げ | docs/pendings.md P-006 | `reset` 側と macOS 版の実機確認を未実施のまま受容(決定シート 論点6 = B。理由「実行できないものは出来なくて当たり前」)。手順番号が反映後の `e2e.md` と一致することを確認して最終化した |
| 棚上げ | docs/pendings.md P-007 | 03 が受容を決めていた1件を pending へ移した(階層の点検の3周目) |
| 気づき | docs/feedbacks/025-... | 「実行できないものは出来なくて当たり前」— 実機確認の未実施を issue ではなく受容として扱う判断基準 |
| 解消した issue | docs/issues/082(削除) | `MODULE-docker-proxy-serve` の `tests:` がコードの実数と一致していなかった件。39 本に揃えて解消 |
| キットの改善 | .claude/improvements/KIT-cs19-section-name-and-test-templates.md | `CS19` が `sections:` を素の見出し名と比べるのに `change-set.md` と `CS1` は `## ` 込みを要求しており、判断の節を持つ変更指示がどちらの書き方でも合格できなかった。人間の合意を得て適用済み |
| キットの改善 | .claude/improvements/KIT-where-technology-decisions-belong.md | 00 は「technology は決めない」と定めるのに決定台帳は人間の技術選定を記録する器でもある。**2026-08-07 に人間が案 A(書いてよい)で裁定**。未適用 |

<!-- 独立レビューについて: 本タスクの `/doc-check` はフェーズ2・フェーズ4 とも **`lens: subagent`**
     で実行した。**Codex はアカウントの利用上限(復旧 2026-08-11)で1本も走っていない**
     (不変則7 が求める明示。代替は決定シート 論点4 = B で人間が承認済み)。
     フェーズ4 の再監査は、行番号アンカーの修正が表の最終セルしか対象にしておらず
     中間セル 12 箇所が残っていたことを検出した — 独立レビューが無ければ
     「直したつもり」で検証済みにしていた。 -->
