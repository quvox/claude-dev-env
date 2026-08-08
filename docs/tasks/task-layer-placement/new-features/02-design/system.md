---
target: docs/02-design/system.md
change: replace
sections:
  - "#### SCR-01 cli-commands"
  - "### E2Eシナリオ一覧"
  - "## 分割の根拠"
  - "## 要件カバレッジ確認"
deletes: []
reason: '決定シート 論点2(人間の回答 = A「表示内容は 01 が持つ」)と `docs/issues/085` の #7〜#9、および `docs/issues/090` の第2層の受け皿を直す。(a) UI 設計の `SCR-01` が**破壊的操作の4状態(確認 / 中止 / 一部失敗 / 残した資源)で何を表示するかの全文**と、「受理できない文字を含む場合は何も削除せず理由を表示して終了コード 1 で終わる」「保持している操作の名前とプロセス ID と再実行の方法を表示し、終了コード 1 で終わる」を持っている。**これらは外から観測できる約束であり 01 の受入基準の持ち物**である(`.claude/directions/02-design.md` の UI design 節: 「would a requirement be unmet if this text were absent?」— いずれも `FR-env-01` 受入基準16・18・23・26・27 と `FR-env-03` 受入基準15・17・18・24 が既に、または本タスクの同じ下降で持つ。**唯一の例外が `FR-env-03` 受入基準14 で、これは削除対象の列挙の全体を `logging.md` へ明示的に委ねている** — したがって UI 節から落とすその1点だけは 01 ではなく `logging.md` が正であり、新しい本文にもそう書く)。**02 の UI 節は「項目と状態の名前」までに戻す**。同じ状態を 01 と 02 の両方が書くと必ずずれる(`.claude/directions/layer-fit.md` §0)。**画面・項目・状態の名前と、受理する文字集合という項目の制約は 02 に残す**(これは項目の型の話であり UI 設計の持ち物である)。(b) 要件カバレッジ確認へ **`FR-env-03-24`(`docs/issues/090` の裁定で 01 に新設する条項)の行を1つ足す** — 主担当は `MOD-cli-logout`(`logout` が所有者コンテナを削除することでこの帰結が生じるため)。**他の行は1つも変えない**。(d) **`/doc-check` の独立レビュー3本が独立に検出した2点を閉じた**: (1) 「唯一の例外」は事実に反する — `logging.md` が単独で持つ表示は削除対象の列挙のほかに2つ(ラベル無しコンテナの表示の限界・`stop` の片付け未実施の案内)あるので、3つを列挙する形へ直した。あわせて指し先の条項から `FR-env-01` 受入基準23・24(どちらも**表示を課さない**条項である)を外した。(2) テスト戦略の E2E-01 行が覆う条項が `FR-env-03` 受入基準 14〜**23** で止まっており、本タスクが新設する受入基準24 を含んでいなかった。同じ下降で `03-impl/tests/e2e.md` に部分手順8-16 を作ったので、範囲を 14〜24 へ広げて手順の新設を明記した。**本文は「深い見出しを先に」の順で並べてある** — `###` を `##` の後ろに置くと本文の中で `##` の子として読め、反映時に**同じ節が2箇所へ書き込まれる**(`.claude/directions/change-set.md` が実測失敗として挙げる型。合成ビューで実際に `### E2Eシナリオ一覧` が2箇所に出ることを確認して直した)。(e2) **`SCR-01` の「状態」行から実装寄りの具体を落とした**: 「実行中=進捗行(イメージ名・バージョン・待機の経過)」の括弧書きと「エラー=**日本語の**原因」の「日本語の」と「空=対象セッションが無い**旨**」の「旨」である。**進捗行の中身と日本語であることの移し先は `docs/02-design/logging.md`**(端末出力の系統がレベル・出力先とあわせて持つ)。`/doc-check` の再監査が「reason が宣言していない編集」として検出したので明記した。(e) `CS8` が E2E-03 行の程度語「通常操作」を検出したので意味を保って直した(→「`CTR-docker-api` が拒否条件と定めない要求」)。**凍結した母集団の CS8 が1件減る方向にしか動かない**。(c) 「分割の根拠」は `CS19` の要求により再読し、**`DSN-mod-01`〜`06` はいずれも継続(変更なし)と判断した**。本タスクは記述の置き場だけを動かし、モジュールの分割も責務も変えないためである'
reflected: 2026-08-08
---

#### SCR-01 cli-commands

| 項目 | 型・制約 | 必須 | 備考 |
|---|---|---|---|
| サブコマンド | 18 種の列挙 | 必須 | 未知の語とヘルプ要求は使い方を表示する |
| 対象セッション名 | 文字列(省略時はカレントディレクトリから導出)。**`stop <name>` に限り `[A-Za-z0-9._-]` のみ受理する** | 任意 | `stop` / `ports` / `forward` など。**受理文字集合の制約は `stop` だけに掛かる**: `stop` は名前をそのまま排他ロックのキー=パス要素として使うため(`CTR-cli-container`「ロックキーとして使える文字」)。**受理できない値を与えられたときに何が起きるかは `FR-env-01` 受入基準18 が定める。** `ports` / `forward` などにはこの制約が掛からない(ロックを取らないため) |
| フラグ | `--no-vnc` / `--kvm` / `--vm` / `--vm-fresh` / `--fresh` / **`--yes`** | 任意 | 非対応の組み合わせは実行前に拒否する。**`--yes` は破壊的操作(`logout` / `reset`)の確認プロンプトを飛ばす**(`D0-env-08` 項3)。端末を持たない環境で破壊的操作を実行する唯一の手段である |

状態: **初期**=使い方の表示 / **実行中**=進捗行 / **エラー**=原因と次の操作の案内 /
**空**=対象セッションが無い / **完了**=接続 URL とアタッチ。

**破壊的操作の状態**(`logout` / `reset`): **確認** / **中止** / **一部失敗** / **残した資源** の4つ。
**`stop` / `reset` が持つ片付けの状態**: **片付け結果** / **片付け未実施**(`stop` だけが持つ)。
**排他待ちで中止の状態**: `start` / `stop` / `logout` / `reset` / `login` / `login-codex` の
**6コマンド共通**である(**破壊的操作だけの状態ではない**: 共有ボリュームまたは docker-proxy を触る
6コマンドすべてがこの状態を持つ)。

**それぞれの状態で利用者に何を示すかは 01 の受入基準が正である**(`FR-env-01` 受入基準
16・18・26・27 / `FR-env-03` 受入基準 15・17・18・24)。**この節は状態の存在と名前だけを
定める** — 表示の内容は外から観測できる約束であり、要件の側が持つ(`.claude/directions/02-design.md`
の UI 設計節)。**ただし 01 が表示を課しておらず `logging.md` だけが持つものが3つある**: 破壊的操作の
削除対象の列挙の全体(`FR-env-03` 受入基準14 自身が `logging.md` を正と定めている)/ ラベルを
持たないため残したコンテナの表示の限界(停止中のものは列挙していない旨)/ `stop` が片付けを
行わなかったことの案内(`FR-env-01` 受入基準23 は削除の禁止だけを課し、表示を課さない)。
ログとしての出力仕様(水準・出力先・文言に課す制約)も `logging.md` が持つ。

### E2Eシナリオ一覧

| E2E ID | 対応 UC | シナリオ | 対象/対象外(理由) |
|---|---|---|---|
| E2E-01 | UC-01 | `claude-dev start`(ブラウザ確認あり / `--no-vnc`)→ `/workspace` マウント・認証・ファイアウォール・tmux → `claude` 起動 → 再実行での再接続。**続けて破壊的操作が「自分が作った資源」にだけ効くことを確認する**: 管理ラベルの付与 / 遊休判定がイメージに依存しないこと / 排他ロックと残骸の引き継ぎ / ラベルを持たない既存コンテナを巻き込まないこと / compose 資源が別プロジェクトを巻き込まないこと / `stop` が受理しない名前 / `logout` がプロジェクト配下の認証コピーを消すこと / 確認と非対話時の中止 / 削除失敗の列挙(`FR-env-01` 受入基準 9・14〜21 / `FR-env-03` 受入基準 14〜24)。**さらにセッション由来の資源の片付けと、`logout` の後にそれが `stop` で回収できないことを確認する**(`FR-env-01` 受入基準 22〜27 / `FR-env-03` 受入基準24。確認する項目と手順は `03-impl/tests/e2e.md` が持つ) | 対象(Must) |
| E2E-02 | UC-02 | `claude-dev forward` → 8100 番台の割当と SSH トンネル → クライアントのブラウザで表示 → `claude-dev ports` で確認 | 対象(Must) |
| E2E-03 | UC-03 | コンテナ内で危険な `docker run` → 拒否 / `/workspace` bind の許可 / **`CTR-docker-api` が拒否条件と定めない要求の透過**。**あわせて、作成されたコンテナとネットワークに所有者ラベルが付いていることを確認する**(`FR-env-07` 受入基準11) | 対象(Must) |
| E2E-04 | UC-04 | `orchestrate` → ブレインストーミング → plan 確定 → worker 並列 → 要判断1件のみ待機・他は継続 → 回答で復帰 → 完了(`make orch-sample` で題材を配置して実走) | 対象(Must) |
| E2E-05 | UC-05 | 実行中に端末を全終了 → `orchestrate` 再実行 → 合流/再開・完了済みの非再実行・plan と履歴の保持 | 対象(Should) |
| E2E-06 | UC-06 | `claude-dev login-codex` → デバイス認証 → 別プロジェクトで `start` → 再ログイン不要で `codex` が起動し、**シェルコマンドが成功して `/workspace` を読み書きできる**。landlock の疎通確認が通り、読み取り専用の明示指定で読み取りが成功する。トークン更新が次のコンテナへ引き継がれる | 対象(Must) |

**全 UC がカバーされている**(UC-01〜UC-06 → E2E-01〜E2E-06)。上流の UC を持たない E2E シナリオは
作らない。

## 分割の根拠

### DSN-mod-01 モジュールは「利用者から見た入口」と1対1にする

- 判断: ホスト CLI をサブコマンド単位で1モジュールに割り、Makefile・スクリプト・Go プログラムも
  それぞれ入口の単位で割る。全 29 モジュール。
- 理由: 変更が起きる単位が入口(サブコマンド・ターゲット・常駐プロセス)であり、影響範囲を
  「どのコマンドが変わるか」で説明できる。旧構成では `cli` が1モジュールで 18 サブコマンドを
  抱えており、`start` の変更と `ports` の変更が同じ影響範囲に見えていた。
- 却下した案: ファイル単位で割る(旧構成) — 1ファイルに 18 の入口が同居し、影響範囲が引けない。
  機能グループ(認証系・ポート系など)で割る — 境界が主観的になり、コードとの1対1が崩れる。

### DSN-mod-02 macOS 実装は同名サブコマンドのモジュールへ相乗りさせる

- 判断: macOS 版(`claude-dev-mac`)を独立モジュール群にせず、同名サブコマンドのモジュールに
  `impl` パスとして相乗りさせる。旧 `cli-mac` モジュールは解体する。
- 理由: `claude-dev-mac` は同じコマンド面の別 OS 実装であり、サブコマンド単位で割ると同一ロジックの
  モジュールが 18 本増えて依存表が読めなくなる。OS 差分は「同じ入口の別実装」として1箇所で
  対比できる方がよい。
- 却下した案: `MOD-cli-mac-*` を 18 本立てる — モジュール数が倍になり、対応要件も重複する。
  旧構成のまま `cli-mac` を1モジュールで残す — `DSN-mod-01` の1対1と矛盾する。

### DSN-mod-03 共有基盤は1モジュールに集約する

- 判断: ホスト CLI の先頭にある定数・ヘルパー関数群を `MOD-cli-common` として独立させる。
- 理由: 全サブコマンドがここへファンインする(実測で 25 関数、最大ファンイン 10)。集約しないと
  18 モジュールが同じ実装パスを重複して持ち、実装とドキュメントの 1 対 1 が崩れる。
- 却下した案: 各サブコマンドのモジュールに複製して書く — 重複により整合検査が落ちる。
  共有基盤を作らず呼び出し関係だけで表す — 境界の無いコードが機能表から漏れる。

### DSN-mod-04 共有するものとプロジェクト単位のものを分ける

- 判断: `docker-proxy` は全 Claude コンテナで共有し、それ以外はプロジェクト単位(またはイメージ単位)
  とする。共有ボリュームは認証・シェル設定・履歴の3本に限る。
- 理由: 共有すると常駐が1つで済む一方、プロジェクト間の干渉が起きうる。干渉が問題になるもの
  (セッション・Chrome プロファイル・運用状態)はプロジェクト単位に置く。
- 却下した案: すべてをプロジェクト単位にする — docker-proxy がプロジェクト数だけ常駐する。
  すべてを共有する — セッションと運用状態が混ざる。

### DSN-mod-05 コールグラフに入口を持たない資産はモジュールにしない

- 判断: コンテナイメージの定義(`Dockerfile.*`)と GHCR 配布ワークフロー(GitHub Actions)は
  モジュール分割定義から外し、`03-impl/environments/`(仕組み)と `03-impl/infra/local/`(構成値)
  に置く。
- 理由: この2つは実行される関数の入口を持たないため、コールグラフに現れない。モジュールとして
  機能表に載せると、機械検査 FT1(入口がコールグラフに存在するか)が重大度「高」で落ち、FT1 は
  落ちると以降の検査を打ち切るゲートであるため、CG1〜CG7 まで含めた機械検査が丸ごと無効になる。
  記述内容は `environments/` と `infra/` が保持するため失われない(`.claude/directions/03-impl.md`
  の「仕組みは environments/、具体的な構成値は infra/」に合致する)。
- 却下した案: モジュールとして残す — 上記のとおり機械検査が無効になる。Dockerfile と GitHub
  Actions のコールグラフ抽出器を作る — このキットの範囲外(`/kit-improve` 案件)。

### DSN-mod-06 モジュールあたりの機能数の上限を超えている2モジュールを許容する

- 判断: `MOD-orchestrator`(19機能)と `MOD-makefile`(19機能)は、1モジュールあたり 15 本という
  分割見直しの目安を超えるが、分割しない。
- 理由: `MOD-orchestrator` は入口が1つ(単一バイナリ)で 219 シンボルを持ち、ファイル境界=責務境界で
  機能へ昇格させた結果が 19 本である。これを1機能に畳むと「1機能=1バイナリ」になり境界が消える。
  逆にモジュールを分けると、単一バイナリが複数モジュールにまたがることになり `DSN-mod-01` の
  1対1が崩れる。`MOD-makefile` も同様に、入口(ターゲット)が 19 個ある単一ファイルである。
- 却下した案: Makefile のターゲットを用途別に束ねる — 束ねた内部に境界が埋没し、記述量は減らない。
  orchestrator を複数モジュールへ割る — 物理配置との1対1が崩れる。

## 要件カバレッジ確認

<!-- 受入基準の**条項ごと**に行を作る(要件ごとではない)。充足の語彙・主担当の規則の正は
     .claude/directions/02-design.md。03 のテスト対応表の「状態」列とは別の列・別の意味。 -->

**`充足` はこの設計がその条項を覆っているか**を言う(4値: `完全` / `部分(P-nn)` / `対象外(理由)` / `-`)。
**実装の達成度・検証状態はここでは言わない** — それは `03-impl/tests/` の各対応表の「状態」列が持つ。
1条項につき主担当モジュールはちょうど1つで、`充足` はその行にだけ書く(非機能要件は条項に分けず
1要件1行。`SR-*` は技術前提であり充足は適用外 = `-`)。

| 受入基準 ID | 割り当てモジュール | 充足 | 根拠 |
|---|---|---|---|
| FR-env-01-1 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-01-2 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-01-3 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-01-4 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-01-5 | MOD-cli-list | 完全 | -(設計判断を要さない) |
| FR-env-01-6 | MOD-cli-stop | 完全 | DSN-env-03, DSN-env-04 |
| FR-env-01-7 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-01-8 | MOD-cli-stop | 完全 | -(設計判断を要さない) |
| FR-env-01-9 | MOD-cli-stop | 完全 | DSN-env-01 |
| FR-env-01-10 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-01-11 | MOD-cli-stop | 完全 | -(設計判断を要さない) |
| FR-env-01-12 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-01-13 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-01-14 | MOD-cli-start | 完全 | DSN-env-01 |
| FR-env-01-15 | MOD-cli-stop | 完全 | DSN-env-01 |
| FR-env-01-16 | MOD-cli-common | 完全 | DSN-env-02 |
| FR-env-01-17 | MOD-cli-common | 完全 | DSN-env-02 |
| FR-env-01-18 | MOD-cli-stop | 完全 | DSN-env-02 |
| FR-env-01-19 | MOD-cli-stop | 部分(P-005) | compose 名の一意化(`DSN-env-03`)で実現するが、ハッシュ先頭6桁の衝突は検出しない設計であり、衝突した2ディレクトリでは一方の `stop` が他方の compose 資源を削除しうる |
| FR-env-01-20 | MOD-cli-stop | 完全 | DSN-env-03 |
| FR-env-01-21 | MOD-cli-stop | 完全 | DSN-env-03 |
| FR-env-01-22 | MOD-cli-stop | 完全 | DSN-env-04 |
| FR-env-01-23 | MOD-cli-stop | 完全 | DSN-env-04 |
| FR-env-01-24 | MOD-cli-stop | 完全 | -(設計判断を要さない) |
| FR-env-01-25 | MOD-cli-reset | 完全 | DSN-env-04 |
| FR-env-01-26 | MOD-cli-stop | 完全 | DSN-env-04。**本条項は `stop` と `reset` の双方に掛かるが、主担当は1つなので `reset` 側の担い手は `MOD-cli-reset`(`FR-env-01-25` の行が持つ)である** |
| FR-env-01-27 | MOD-cli-stop | 完全 | -(設計判断を要さない)。**`reset` 側の担い手は `FR-env-01-26` の根拠欄と同じ** |
| FR-env-02-1 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-02-2 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-02-3 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-02-4 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-02-5 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-02-6 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-03-1 | MOD-cli-login | 完全 | -(設計判断を要さない) |
| FR-env-03-2 | MOD-cli-start | 完全 | DSN-auth-01 |
| FR-env-03-3 | MOD-entrypoint | 完全 | DSN-auth-01 |
| FR-env-03-4 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-03-5 | MOD-cli-logout | 完全 | DSN-env-01 |
| FR-env-03-6 | MOD-cli-login-codex | 完全 | -(設計判断を要さない) |
| FR-env-03-7 | MOD-cli-start | 完全 | DSN-auth-01 |
| FR-env-03-8 | MOD-entrypoint | 完全 | DSN-auth-01 |
| FR-env-03-9 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-03-10 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-03-11 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-03-12 | MOD-cli-login | 完全 | -(設計判断を要さない) |
| FR-env-03-13 | MOD-cli-login-codex | 完全 | -(設計判断を要さない) |
| FR-env-03-14 | MOD-cli-logout | 完全 | -(設計判断を要さない) |
| FR-env-03-15 | MOD-cli-logout | 完全 | -(設計判断を要さない) |
| FR-env-03-16 | MOD-cli-logout | 完全 | -(設計判断を要さない) |
| FR-env-03-17 | MOD-cli-logout | 完全 | DSN-env-01 |
| FR-env-03-18 | MOD-cli-logout | 完全 | -(設計判断を要さない) |
| FR-env-03-19 | MOD-cli-logout | 完全 | -(設計判断を要さない) |
| FR-env-03-20 | MOD-cli-logout | 完全 | -(設計判断を要さない) |
| FR-env-03-21 | MOD-cli-logout | 完全 | -(設計判断を要さない) |
| FR-env-03-22 | MOD-cli-reset | 完全 | -(設計判断を要さない) |
| FR-env-03-23 | MOD-cli-logout | 完全 | -(設計判断を要さない) |
| FR-env-03-24 | MOD-cli-logout | 完全 | DSN-env-04(所有者ラベルの照合値は所有者の Claude コンテナにしか無いため、`logout` がそれを削除すると `stop` では引けなくなる。規則 D と `CTR-cli-container`「削除対象の決め方」が持つ) |
| FR-env-04-1 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-04-2 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-04-3 | MOD-cli-ssh-keys | 完全 | -(設計判断を要さない) |
| FR-env-04-4 | MOD-cli-ssh-keys | 完全 | -(設計判断を要さない) |
| FR-env-04-5 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-04-6 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-04-7 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-05-1 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-05-2 | MOD-cli-common | 完全 | -(設計判断を要さない) |
| FR-env-05-3 | MOD-firewall | 完全 | -(設計判断を要さない) |
| FR-env-05-4 | MOD-firewall | 完全 | -(設計判断を要さない) |
| FR-env-05-5 | MOD-entrypoint | 完全 | DSN-fw-01 |
| FR-env-05-6 | MOD-firewall | 完全 | -(設計判断を要さない) |
| FR-env-05-7 | MOD-firewall | 完全 | -(設計判断を要さない) |
| FR-env-06-1 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-06-2 | MOD-cli-forward | 完全 | -(設計判断を要さない) |
| FR-env-06-3 | MOD-cli-unforward | 完全 | -(設計判断を要さない) |
| FR-env-06-4 | MOD-cli-ports | 完全 | -(設計判断を要さない) |
| FR-env-06-5 | MOD-cli-forward | 完全 | -(設計判断を要さない) |
| FR-env-06-6 | MOD-cli-forward | 完全 | -(設計判断を要さない) |
| FR-env-06-7 | MOD-cli-forward | 完全 | -(設計判断を要さない) |
| FR-env-06-8 | MOD-cli-forward | 完全 | -(設計判断を要さない) |
| FR-env-06-9 | MOD-cli-forward | 完全 | -(設計判断を要さない) |
| FR-env-06-10 | MOD-cli-forward | 完全 | -(設計判断を要さない) |
| FR-env-06-11 | MOD-cli-forward | 完全 | -(設計判断を要さない) |
| FR-env-06-12 | MOD-cli-unforward | 完全 | -(設計判断を要さない) |
| FR-env-06-13 | MOD-cli-forward | 完全 | -(設計判断を要さない) |
| FR-env-07-1 | MOD-cli-start | 完全 | DSN-arch-01 |
| FR-env-07-2 | MOD-docker-proxy | 完全 | -(設計判断を要さない) |
| FR-env-07-3 | MOD-docker-proxy | 完全 | -(設計判断を要さない) |
| FR-env-07-4 | MOD-cli-common | 完全 | -(設計判断を要さない) |
| FR-env-07-5 | MOD-cli-start | 部分(P-005) | 一意化(`DSN-env-03` = `FR-env-01-19` と同じ機構)で実現するが、ハッシュ先頭6桁の衝突時は名前が一意にならない(衝突検出を設計しない) |
| FR-env-07-6 | MOD-docker-proxy | 完全 | DSN-dp-02 |
| FR-env-07-7 | MOD-docker-proxy | 完全 | DSN-dp-01 |
| FR-env-07-8 | MOD-docker-proxy | 完全 | DSN-dp-01 |
| FR-env-07-9 | MOD-docker-proxy | 完全 | -(設計判断を要さない) |
| FR-env-07-10 | MOD-docker-proxy | 完全 | -(設計判断を要さない) |
| FR-env-07-11 | MOD-docker-proxy | 完全 | DSN-env-04 |
| FR-env-07-12 | MOD-docker-proxy | 完全 | DSN-dp-01(判定できない入力は通す。`DSN-env-04` がこの倒し方を採る) |
| FR-env-08-1 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-08-2 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-08-3 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-08-4 | MOD-vm-mode | 完全 | -(設計判断を要さない) |
| FR-env-08-5 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-08-6 | MOD-vm-mode | 完全 | -(設計判断を要さない) |
| FR-env-08-7 | MOD-vm-mode | 完全 | -(設計判断を要さない) |
| FR-env-08-8 | MOD-vm-mode | 完全 | -(設計判断を要さない) |
| FR-env-09-1 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | -(設計判断を要さない) |
| FR-env-09-2 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | -(設計判断を要さない) |
| FR-env-09-3 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | -(設計判断を要さない) |
| FR-env-09-4 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | -(設計判断を要さない) |
| FR-env-09-5 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | -(設計判断を要さない) |
| FR-env-09-6 | MOD-cli-pull | 完全 | -(設計判断を要さない) |
| FR-env-09-7 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | -(設計判断を要さない) |
| FR-env-09-8 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | DSN-dist-01 |
| FR-env-09-9 | MOD-cli-pull | 完全 | -(設計判断を要さない) |
| FR-env-09-10 | MOD-cli-pull | 完全 | -(設計判断を要さない) |
| FR-env-09-11 | MOD-cli-pull | 完全 | -(設計判断を要さない) |
| FR-env-10-1 | MOD-makefile | 完全 | -(設計判断を要さない) |
| FR-env-10-2 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-10-3 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | -(設計判断を要さない) |
| FR-env-10-4 | MOD-cli-common | 完全 | -(設計判断を要さない) |
| FR-env-10-5 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-10-6 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-11-1 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-11-2 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-11-3 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | -(設計判断を要さない) |
| FR-env-11-4 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-11-5 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-11-6 | MOD-cli-start | 完全 | DSN-mod-04 |
| FR-env-11-7 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-11-8 | MOD-cli-common | 完全 | -(設計判断を要さない) |
| FR-env-12-1 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | DSN-dist-01 |
| FR-env-12-2 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | -(設計判断を要さない) |
| FR-env-12-3 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | DSN-dist-01 |
| FR-env-12-4 | MOD-entrypoint | 完全 | DSN-dist-02 |
| FR-env-12-5 | MOD-entrypoint | 完全 | DSN-dist-02 |
| FR-env-12-6 | MOD-entrypoint | 完全 | DSN-dist-02 |
| FR-env-12-7 | MOD-cli-start | 完全 | DSN-dist-02 |
| FR-env-12-8 | MOD-entrypoint | 完全 | DSN-dist-02 |
| FR-env-12-9 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | DSN-dist-02 |
| FR-env-12-10 | MOD-entrypoint | 完全 | DSN-dist-02 |
| FR-env-12-11 | MOD-entrypoint | 完全 | DSN-dist-02 |
| FR-env-12-12 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 対象外(オーケストレーターが codex を worker/レビューアーとして常用するかは未決で、01 自身が本要件の対象外と定める) | D0-orch-17 |
| FR-orch-01-1 | MOD-cli-orchestrate | 完全 | -(設計判断を要さない) |
| FR-orch-01-2 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-01-3 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-01-4 | MOD-orchestrator | 完全 | DSN-arch-02 |
| FR-orch-01-5 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-01-6 | MOD-orchestrator | 完全 | DSN-ui-01 |
| FR-orch-01-7 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-02-1 | MOD-orchestrator | 完全 | DSN-orch-01 |
| FR-orch-02-2 | MOD-orchestrator | 完全 | DSN-orch-02 |
| FR-orch-02-3 | MOD-orchestrator | 完全 | DSN-prompt-03 |
| FR-orch-02-4 | MOD-cli-orchestrate | 完全 | DSN-orch-02 |
| FR-orch-02-5 | MOD-cli-orchestrate | 完全 | -(設計判断を要さない) |
| FR-orch-03-1 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-2 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-3 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-4 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-5 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-6 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-7 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-8 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-9 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-10 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-11 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-04-1 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-04-2 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-04-3 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-04-4 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-04-5 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-04-6 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-04-7 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-04-8 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-04-9 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-05-1 | MOD-orchestrator | 完全 | DSN-log-02 |
| FR-orch-05-2 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-05-3 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-05-4 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-05-5 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-05-6 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-05-7 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-05-8 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-05-9 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-05-10 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-06-1 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-06-2 | MOD-orchestrator | 完全 | DSN-prompt-02 |
| FR-orch-06-3 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-06-4 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-06-5 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-06-6 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-06-7 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-07-1 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-07-2 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-07-3 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-07-4 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-07-5 | MOD-hooks | 完全 | -(設計判断を要さない) |
| FR-orch-07-6 | MOD-hooks | 完全 | -(設計判断を要さない) |
| FR-orch-08-1 | MOD-orchestrator | 完全 | DSN-ui-02 |
| FR-orch-08-2 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-08-3 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-08-4 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-08-5 | MOD-orchestrator | 完全 | DSN-prompt-01 |
| FR-orch-08-6 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-08-7 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-08-8 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-09-1 | MOD-sample-project | 完全 | -(設計判断を要さない) |
| FR-orch-09-2 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-09-3 | MOD-sample-project | 完全 | -(設計判断を要さない) |
| FR-orch-09-4 | MOD-sample-project | 完全 | -(設計判断を要さない) |
| FR-orch-09-5 | MOD-sample-project | 完全 | -(設計判断を要さない) |
| FR-orch-09-6 | MOD-sample-project | 完全 | -(設計判断を要さない) |
| NFR-perf-01 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | DSN-dist-01 |
| NFR-perf-02 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | DSN-dist-01 |
| NFR-perf-03 | MOD-orchestrator | 完全 | DSN-prompt-03 |
| NFR-avail-01 | MOD-orchestrator, MOD-cli-orchestrate | 完全 | DSN-orch-02 |
| NFR-avail-02 | MOD-cli-start, MOD-entrypoint | 完全 | -(設計判断を要さない) |
| NFR-avail-03 | MOD-entrypoint, MOD-firewall, MOD-orchestrator, MOD-hooks, MOD-vm-mode | 完全 | DSN-fw-01(ファイアウォール分。他の補助機能の失敗許容は各契約のエラーケースが定める) |
| NFR-sec-01 | MOD-docker-proxy, MOD-firewall, MOD-cli-start, MOD-cli-common | 完全 | DSN-arch-01 |
| NFR-sec-03 | MOD-orchestrator, MOD-hooks | 完全 | -(設計判断を要さない) |
| NFR-ops-02 | MOD-cli-common, 各 MOD-cli-*, MOD-entrypoint | 完全 | DSN-arch-01 |
| NFR-ops-03 | MOD-makefile, MOD-cli-common | 完全 | -(設計判断を要さない) |
| NFR-ops-04 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| NFR-scale-01 | MOD-cli-start, MOD-cli-common, MOD-cli-forward | 完全 | DSN-env-03 |
| NFR-scale-02 | MOD-cli-login-codex, MOD-cli-logout, MOD-entrypoint | 完全 | DSN-auth-01 |
| SR-01 | MOD-cli-common, MOD-cli-setup | - | SR-01(技術前提。充足は適用外)。前提コマンドの検査とインフラ作成が Docker の存在に依存する |
| SR-02 | MOD-entrypoint, MOD-firewall, MOD-docker-proxy, (モジュール外)`03-impl/environments/images.md` | - | SR-02(技術前提。充足は適用外)。OS 依存はホスト CLI 側に閉じる(`DSN-mod-02`) |
| SR-03 | MOD-cli-login, MOD-cli-login-codex, MOD-cli-common, (モジュール外)`03-impl/environments/images.md` | - | SR-03(技術前提。充足は適用外)。認証は共有ボリューム経由のみ。イメージへ焼き込まない |
| SR-04 | MOD-cli-start, MOD-docker-proxy, (担い手)`02-design/environments.md`「Codex実行設定」 | - | SR-04(技術前提。充足は適用外)。`--security-opt` を付けない=既定の confinement を維持する |
| SR-05 | (担い手)`00-requests/request.md`「やらないこと」2 | - | SR-05(技術前提。充足は適用外)。利用前提。設計上の実装物を持たない |
| SR-10 | MOD-cli-common, MOD-makefile | - | SR-10(技術前提。充足は適用外)。前提コマンド検査と `make setup` の対象環境 |
| SR-11 | MOD-cli-common | - | SR-11(技術前提。充足は適用外)。Docker API の版に依存する判定を持つ |
| SR-12 | MOD-cli-common | - | SR-12(技術前提。充足は適用外)。不足コマンドを列挙して導入方法を案内する |
| SR-13 | (モジュール外)`03-impl/infra/local/ghcr.md` | - | SR-13(技術前提。充足は適用外)。マルチアーキ配布は CI が担う(`DSN-mod-05`) |
| SR-14 | MOD-vm-mode, MOD-cli-start | - | SR-14(技術前提。充足は適用外)。`/dev/kvm` の有無で分岐する。macOS では提供しない |
| SR-15 | MOD-cli-login, MOD-cli-login-codex | - | SR-15(技術前提。充足は適用外)。認証方式の選択そのもの |
| SR-20 | MOD-cli-common, 各 MOD-cli-*, MOD-makefile, MOD-portsync, MOD-vm-mode, MOD-entrypoint, MOD-firewall, MOD-container-tools | - | SR-20(技術前提。充足は適用外)。Bash 実装のモジュール群 |
| SR-21 | MOD-docker-proxy, MOD-orchestrator | - | SR-21(技術前提。充足は適用外)。Go 実装の2モジュール |
| SR-22 | MOD-orchestrator | - | SR-22(技術前提。充足は適用外)。TUI のみ外部依存を許容し vendor へ同梱する |
| SR-23 | MOD-sample-project | - | SR-23(技術前提。充足は適用外)。Python + pytest の自己検証題材 |
| SR-24 | (モジュール外)`03-impl/environments/images.md` | - | SR-24(技術前提。充足は適用外)。マルチステージと終端レイヤー(`DSN-dist-01` / `DSN-mod-05`) |
| SR-30 | MOD-makefile | - | SR-30(技術前提。充足は適用外)。単一の入口 |
| SR-31 | MOD-docker-proxy, MOD-orchestrator | - | SR-31(技術前提。充足は適用外)。実コマンドは `environments.md` が正 |
| SR-32 | (担い手)本書「テスト戦略」`DSN-test-01` | - | SR-32(技術前提。充足は適用外)。自動テストを設けないという明示的な割り切り |
| SR-33 | (モジュール外)`03-impl/infra/local/ghcr.md` | - | SR-33(技術前提。充足は適用外)。GitHub Actions の日次実行 |
| SR-34 | (担い手)`02-design/environments.md`「Codex実行設定」 | - | SR-34(技術前提。充足は適用外)。legacy landlock で confinement を緩めずに実行する |

**システム要件(`SR-nn`)の行**について: SR は「システムが満たす振る舞い」ではなく**技術前提と制約**
であるため充足を持たない(`充足` = `-`。`.claude/directions/01-requirements.md` が定める)。
担い手がモジュールでないものは、その制約を保持する 02 のドキュメントを担い手として書く
(空欄を作らないための規約)。

**要件を持たないモジュールは無い**(全 29 モジュールが「モジュール分割定義」の対応要件と上表の
いずれかに現れる)。**割り当て先の無い条項も無い**(機能要件の全 210 条項・NFR 13 件・SR 21 件が
すべて上表に現れる)。
