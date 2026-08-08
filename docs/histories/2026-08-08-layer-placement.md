---
id: 2026-08-08-layer-placement
date: 2026-08-08
task: task-layer-placement
origin_layer: 00
issue: docs/issues/086-modify-upper-layers-carry-implementation-mechanisms.md
summary: 上位層(00/01)が持っていた実装の機構と、02 が持っていた実装の細部を、それぞれ本来属する層へ移した(issues 083・085・086・090・091 を解消)
---

<!-- タスクごとに1ファイル。追記のみ(確定したエントリの文章は書き換えない)。 -->

# 2026-08-08 記述を本来あるべき層へ移す(層の帰属の是正)

## 変更理由

**上位層が実装の機構を持っていた。** 00 の決定と用語集に実装ファイルの行番号・環境変数名・
起動順・配列名が入り、01 の受入基準が下位層 ID(`CTR-*` / `MODULE-*` / `DSN-*`)と実装ファイル名を
名指し、02 が実装のシンボル名・実行順序・出力文言・03 の実数を持っていた。
CLAUDE.md 原則3 の「読む向き」(層の帰属)に反する状態で、機械検査 `CS18` が 01 について 17 件を
検出していたほか、**機械が見ないパターン**が `docs/issues/086` に 59 件記録されていた。

**起点層は 00**。`086` の最重要5件が 00 の決定と用語集にあり、`090`・`091` は `D0-env-05` 項2 と
`D0-env-08` 項8 の**理由文そのもの**を直すため、`D0-scope-02` の委任では扱えない
(00 の意味に触れる編集を含むので、フェーズ1 の決定シートで人間の合意を取った ——
一括回答「全て推奨で良い」)。

**コードは1行も変えていない。** `docs/issues/085` / `086` の「正はどちらか」がそろって
「要件・設計が正、実装の誤りではない」と裁定済みだったためである。

## 変更内容の要約

- **00 から実装の機構を落とした**(移し先に事実が在ることを1件ずつ確認してから落としたので情報は
  失われていない)。例: `D0-sec-09` の `iptables`、`D0-env-04` の `uname -s` 判定と symlink の手順、
  `D0-env-02` のクライアント側の接続手順、用語集の `BLACKLIST_DOMAINS` の同梱16件と
  `.orchestrator/` のファイル名、`D0-orch-18` の `orchestrator/trigger.go::Evaluate`。
  **人間が選んだ技術そのもの(何を使うか)は 00 に残した** — 落としたのは「どう使うか」だけである。
- **`D0-dist-03` 項1・項3 と `D0-dist-04` 項1・項2 が 02 の `DSN-dist-01` と同じ主張を独立に
  持っていた**(所有者が2つ)ので、実現手段の側を落とした。
- **01 の条項から下位層 ID と実装ファイル名を落とした**(`CS18` 17 件 → 0 件)。
  受入基準は「外から観測できること」だけを言い、機構の指し先は 02/03 に一本化した。
- **02 から実装のシンボル名・実行順序・出力文言・03 の実数を落とした**。
  `system.md` の UI 設計 `SCR-01` は「項目と状態の名前」までに戻し、表示の全文は 01 の受入基準へ、
  ログとしての出力仕様は `logging.md` へ寄せた(**この線を `system.md` の UI 節に明文で書いた** ——
  独立レビュー2本が `logging.md` を「所有者が2つ」と指摘したが、規範の割り当てを根拠に誤検知と
  裁定したうえで、線が曖昧だった事実に手当てをした)。
- **`docs/issues/090` の裁定 A を4層に分けて書いた**: 決定と理由は `D0-env-05` 項2、
  利用者から見た帰結は **`FR-env-03` 受入基準24(新設条項 `FR-env-03-24`)**、機構は
  `CTR-cli-container`「削除対象の決め方(4つの規則)」、実装の事実は
  `MODULE-cli-logout`「既知の制限」(閾値の外へ移した)。
- **`docs/issues/091` の裁定 A を 00 だけに書いた**: `D0-env-08` 項8 に「`reset` が所有者を
  問わない理由」(初期状態へ戻す操作なので所有者で絞ると目的を果たせない)を足した。
- **新設条項 `FR-env-03-24` の受け皿を 02・03 の両側に作った**:
  02 の要件カバレッジ表に1行、`03-impl/tests/cli-logout.md` の対応表に1行、
  そして**実機確認手順として E2E-01 手順8-16 を新設**した(既存の後片付けは手順8-17 へ繰り下げ)。
  **フェーズ2 の下降はこの手順を作っておらず、対応表の指し先が空だった** ——
  独立レビュー3本が独立に検出した重大度「高」である。
- **同型の空手形をもう1件閉じた**: `NFR-sec-03` の測定方法が指す「E2E-04 で `env` を確認する」
  手順が実在しなかったので、E2E-04 に手順8 を新設した。
  **この2件で「`03-impl/tests/` の識別子欄が指す実機確認手順が実在しない」箇所は 0 件になった。**
- **移送の片側落ちを1件直した**: `03-impl/tests/strategy.md` が持っていたカバレッジ計測コマンドを
  `02-design/environments.md`「lint・テストコマンド」へ移し、03 側は指し先だけにした
  (`.claude/directions/02-design.md`「The command strings written here are authoritative」)。
  あわせて条項数の数え直し(209 → **210 条項** / 対応表 224 → **225 行** / 条項 222 → **223 件**)を行った。
- **程度語「通常」を、変更指示が触った節について意味を保って直した**(`CS8` 42 → 32 件)。

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/00-requests/acceptances.md | 1.2.0 → 1.3.0 | `AC-02`・`AC-03` から実装の機構(noVNC のポート番号帯の根拠・Docker API の検査位置)を落とし、受け入れの判定だけにした |
| docs/00-requests/terminology.md | 1.3.0 → 1.4.0 | 「ブロック対象ドメイン」の同梱16件と配列の中身、「資源逼迫」の上書き手段、「運用状態」のファイル名を 03 の実装仕様への指し先に替えた |
| docs/00-requests/decisions/auth.md | 1.2.0 → 1.3.0 | `D0-auth-02`・`D0-auth-03` から書き戻しの実装手順(周期の実現方法・コピー元パス)を落とし、決定と理由だけにした |
| docs/00-requests/decisions/dist.md | 1.0.1 → 1.1.0 | `D0-dist-03`・`D0-dist-04` から `DSN-dist-01` と重複する実現手段(終端レイヤーへの配置・キャッシュキーの作り方)を落とした |
| docs/00-requests/decisions/env.md | 1.3.0 → 1.4.0 | `D0-env-02`(接続手順)・`D0-env-04`(`uname -s` と symlink)・`D0-env-05` 項2(帰結の断定を決定と理由へ)・`D0-env-06`(付与位置は残し変数名と値の形式を 02 へ)・`D0-env-08` 項8(`reset` が所有者を問わない理由を追記 = `docs/issues/091`) |
| docs/00-requests/decisions/orch.md | 1.3.0 → 1.4.0 | `D0-orch-18` から `orchestrator/trigger.go::Evaluate` を落とし、「下表の発火条件のいずれにも当たらない場合」という決定の言葉に直した |
| docs/00-requests/decisions/sec.md | 1.1.2 → 1.2.0 | `D0-sec-09` から `iptables` を落とし、`D0-sec-04` の委任範囲を「規則をどこに置くか」へ一般化した(「チェイン」が 00 に根拠を持たなくなるため)。`D0-sec-08`・`D0-sec-10` も同様 |
| docs/01-requirements/functional.md | 1.11.0 → 1.12.0 | 15 要件の受入基準から下位層 ID と実装ファイル名を落とし、**`FR-env-03-24` を新設**(`logout` 後にセッション由来の資源が `stop` で回収できないこと)。条項 ID は1つも動かしていない(`CS16`) |
| docs/01-requirements/non-functional.md | 1.5.0 → 1.6.0 | 4分類の測定方法から実装の識別子を落とした。`NFR-ops-02` の測定方法は**残した**(受け皿が `03-impl/tests/cli-common.md` に実在し、落とすと目標値「OS 分岐が 0 件」を測れなくなるため) |
| docs/01-requirements/usecases.md | 1.3.0 → 1.4.0 | `UC-01`・`UC-03`・`UC-06`・シナリオ外要件から機構を落とし、`FR-env-12-9` / `UC-06` A3 の空手形の指し先を `D0-dist-04` 項6 へ直した |
| docs/02-design/contracts/cli-container.md | 1.6.0 → 1.7.0 | 「削除対象の決め方(4つの規則)」に**所有者ラベルの照合値が所有者コンテナにしか無いこと**(`docs/issues/090` の第3層)を書き、「排他(ロックキー)」から実装のシンボル名を落とした |
| docs/02-design/contracts/cli-orchestrator.md | 1.1.0 → 1.2.0 | 「受け渡す設定」と `DSN-orch-02 の適用` から実装の関数名・字句解析の手順を落とし、契約としての取り決めだけにした |
| docs/02-design/environments.md | 1.1.0 → 1.2.0 | 「lint・テストコマンド」に**カバレッジ計測(docker-proxy)**と `relations-query.py --health` の行を足し(03 からの移送先)、「コンテナ・実行環境」に SSH の接続手順の受け皿を作った |
| docs/02-design/relations.md | 1.6.0 → 1.7.0 | `PLAN-cli-reset` / `PLAN-entrypoint-claude` / `PLAN-cli-common-*` から実装のシンボル名と実数を落とし、ツール名の直書きを `environments.md` への指し先にした |
| docs/02-design/system.md | 2.7.0 → 2.8.0 | UI 設計 `SCR-01` を「項目と状態の名前」までに戻し、E2E シナリオ一覧に手順8-16 を明記、要件カバレッジ確認に `FR-env-03-24` の行を追加(主担当 `MOD-cli-logout`)、「分割の根拠」`DSN-mod-01`〜`06` を再読して全件継続 |
| docs/03-impl/relations/MODULE-cli-logout.md | 版なし(層代表は index.md) | 「既知の制限」のセッション由来資源の行を**閾値の外**へ移した(`D0-env-05` 項2 が承知のうえで置いた範囲であり、帰結は `FR-env-03-24` が持つ)。「実装上の判断」14 件は現物のコードで再読して**全件継続**、判断4 の程度語だけ意味を保って直した |
| docs/03-impl/tests/cli-logout.md | 1.4.0 → 1.5.0 | `FR-env-03-24` の行(状態は `未検証(テスト未実装)`。指し先は E2E-01 手順8-16)と、**新設した「テスト設計の判断」3件**を追加 |
| docs/03-impl/tests/e2e.md | 1.3.0 → 1.4.0 | E2E-01 に部分手順16 を新設し後片付けを 8-17 へ繰り下げ、E2E-04 に手順8 を新設。既存の判断4件は継続、`[DS-01]` の開示行を1件追加 |
| docs/03-impl/tests/strategy.md | 1.3.0 → 1.4.0 | カバレッジ計測コマンドを `environments.md` への指し先に替え、集計値を 210 条項 / 225 行 / 223 件へ数え直した |
| docs/03-impl/index.md | 1.17.0 → 1.18.0 | 「実装の欠陥として起票済み」から `090` / `091` を解消済みとして外し、`check-relations.py` の実行日を更新 |

## 実装したもの

| 対象 | 内容 | コミット |
|---|---|---|
| (なし) | **コードは1行も変えていない。** 記述の置き場だけを動かした。`git diff --name-only 914d840..HEAD` の非 `docs/` 差分は 0 件 | — |

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 変更 | MODULE-cli-logout | 「既知の制限」のセッション由来資源の行を閾値の外へ移し、`docs/issues/090` への参照を外した。frontmatter(`impl` / `callers` / `callees` / `contracts` / `design` / `tests`)は**1文字も変えていない**(コード無変更のため) |
| 追加・削除 | (なし) | — |

コードから再生成したコールグラフ・機能表・`feature-graph.md` は**差分 0**(`build-callgraphs.py --check`
と `cluster-features.py --check` がいずれも「最新」)。`callgraph-check.py` は 高 0 / 中 6 / 低 21 / 参考 20 で、
**中の 6 件は CG3 の既知の誤検知**(shell の `exec` 起動とインターフェース越しのディスパッチを抽出器が
辺として出せないだけで、relations 本文は根拠を持つ)。

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 解消した issue | docs/issues/083(削除) | 01 の条項が下位層 ID と実装ファイル名を名指す 16 件。`CS18` が 0 件になった |
| 解消した issue | docs/issues/085(削除) | 02 が実装のシンボル名・実行順序・出力文言・03 の実数を持つ 11 件 |
| 解消した issue | docs/issues/086(削除) | 00・01 が実装の機構を持つ 59 件(`CS18` が見ないパターン。本タスクの起点) |
| 解消した issue | docs/issues/090(削除) | `logout` が作る孤児資源の帰結を4層に分けて書いた |
| 解消した issue | docs/issues/091(削除) | `D0-env-08` 項8 に `reset` が所有者を問わない理由を書いた |
| 記述の訂正 | docs/issues/084 | 「テスト設計の判断」の欠落が 27 件 → **26 件**(`cli-logout.md` を埋めた分)。残りは 084 のまま |
| 記述の訂正 | docs/issues/078 | YAML 解析に失敗する frontmatter 5件のうち `issues/083` が削除されたので **4件**へ |
| 棚上げの追記 | docs/pendings.md P-006 | 新設した E2E-01 **手順8-16** を対象に追加(手順8-15 と同じ専有ホストを要するため) |
| 新規 issue | docs/issues/093 | `FR-env-12-12` が受入基準ではない条項 ID である(フェーズ2 で起票。本タスクでは解消しない) |
| 新規 issue | docs/issues/094 | 利用者が見る値が複数層に逐語で在る(4件のべ13箇所) |
| 新規 issue | docs/issues/095 | 程度語「通常」が 34 箇所(本タスクの反映後は 32 箇所) |
| キット側の欠陥(**行き先が `docs/` に無い**) | 下の「キットへの申し送り」 | `CS17` が DS-07 / DS-08 の規範どおりの開示を違反と判定する |

## キットへの申し送り(`/kit-improve` 案件。`docs/issues/` に置けないもの)

**`.claude/directions/delegation.md` §2 は DS-08(進め方)の開示先を「`memo.md` のタスクリスト」、
DS-07 を「開示不要」と定めているのに、`check-changeset.py` の `CS17` (b) は `memo.md` にある
角括弧つきの DS 表記が変更指示のどこにも無ければ違反とする**(実装は
`.claude/scripts/check-changeset.py:1083` の `DS_MARK` と `:1111-1116`)。
したがって **DS-08 を規範どおりの場所に規範どおりの書式で開示すると必ず `CS17` 違反になり**、
消す唯一の方法は「進め方」を変更指示(= SSOT)へ書くことで、それは仕様ではないので誤りである。
8 行のうち **DS-07 と DS-08 の2行**がこの矛盾に当たる。

**2026-08-08 の `/implement` で実測した** — 角括弧つきで書いたところ
`CS17` が「memo.md: DS-08 を行使したと memo.md に在るのに、変更指示のどこにも開示が無い」を出して
不合格になり、角括弧を外して回避した。

**`docs/issues/` に起票していない理由**: 直しが始まるのは `.claude/`(キット)であって 00〜03 の
どれでもなく、`CS20` が要求する `origin_layer` の4値に正直に当てはまる値が無い(嘘の層を書くと
`/task-new` がそれを引き継いで下流だけを直す —— `.claude/directions/layer-fit.md` §4 が防いでいる失敗)。
キットの行き先である `.claude/improvements/` は **`/kit-improve` だけが書ける**
(`.claude/improvements/README.md`)。**人間が `/kit-improve` を起動するのが唯一の経路である。**

## 恒久的に真な事実(タスクの調査メモから移したもの)

- **コード無変更のタスクでは、タスク配下の staged コールグラフを生成しない。**
  `resolve-callgraph-out.py` は `new-features/03-impl/callgraphs` を返すが、生成すると SSOT の複製に
  なるうえ、`docs/issues/076` の不具合で `check-changeset.py` が CS1 違反 29 件を出して
  フェーズ3 のゲートが通らなくなる(076 の「経緯」が前タスクの `/implement` で実測している)。
  代わりに `build-callgraphs.py --check` / `cluster-features.py --check` /
  `callgraph-check.py --to-be <slug>` の3本でコード ⇄ 03 の一致を確かめる。
- **`callgraph-check.py` の中 6 件(CG3)は既知の誤検知**である。`MODULE-entrypoint-claude` →
  `MODULE-firewall-init` / `MODULE-portsync-dood` / `MODULE-vm-mode-up`、
  `MODULE-orchestrator-controller` → `MODULE-orchestrator-slack`、
  `MODULE-orchestrator-review` / `MODULE-orchestrator-worker` → `MODULE-orchestrator-claude-exec`。
  いずれも shell の `exec` 起動かインターフェース越しのディスパッチで、抽出器が辺を出せないだけである。
- **02 ⇄ 03 の連携差分は 0 件**: PLAN 64 件すべてに `MODULE-*` があり、MODULE のみ 19 件は
  `docs/02-design/relations.md` の除外宣言(`MOD-orchestrator` の内部関数 18 本 + 自己検証題材の実装本体)と
  全件一致する。
