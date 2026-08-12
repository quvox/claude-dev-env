---
id: MODULE-cli-common-destructive
updated: 2026-08-12
module: MOD-cli-common
kind: function-call
sync: sync
impl: claude-dev::destructive_plan, claude-dev::destructive_rm, claude-dev::destructive_deleted, claude-dev::destructive_failed, claude-dev::destructive_skipped, claude-dev::destructive_report, claude-dev::destructive_arm_interrupt, claude-dev::destructive_abort_if_interrupted, claude-dev-mac::destructive_plan, claude-dev-mac::destructive_rm, claude-dev-mac::destructive_deleted, claude-dev-mac::destructive_failed, claude-dev-mac::destructive_skipped, claude-dev-mac::destructive_report, claude-dev-mac::destructive_arm_interrupt, claude-dev-mac::destructive_abort_if_interrupted
callers: MODULE-cli-logout, MODULE-cli-reset
callees: なし
contracts: CTR-cli-container
design: DSN-mod-02, DSN-mod-03, DSN-mod-07
requirements: FR-env-01, FR-env-03
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
summary: 削除の計画・実行・結果の記録と、中断要求の遅延を扱う共通手順
---

# MODULE-cli-common-destructive 削除結果の記録と中断の遅延

## 目的

`logout` と `reset` が「削除できなかった資源を1件ずつ列挙して終了コード 1 で終わる」
(`FR-env-03` 受入基準18)と「`INT` / `TERM` は進行中の1件を終えてから受け、そこまでの結果を
列挙して終了コード 130 で終わる」(同23)を**同一の手順で**満たすための共通基盤である。

**`stop` はこの手順を使わない。** `stop` は削除の失敗を握って続行する仕様であり
(`FR-env-01` 受入基準11・24。`D0-env-08` 項5 が `stop` だけを例外としている)、
「消えなかった資源を列挙して非0で終わる」という本手順の目的と逆を向いているためである。
用語集の「破壊的操作」は `stop` / `logout` / `reset` の3サブコマンドを指すが、
**本機能を共有するのはそのうち2つである**。

## 処理の流れ

モジュール水準の4変数(`_DESTRUCTIVE_PENDING` / `_DESTRUCTIVE_DELETED` / `_DESTRUCTIVE_FAILED` /
`_DESTRUCTIVE_INTERRUPTED`)を状態として持ち、次の8つの入口で操作する
(`claude-dev:634`-`:700` / `claude-dev-mac:699`-`:765`)。

1. `destructive_plan <表示名>` — 削除予定として `_DESTRUCTIVE_PENDING` に積む。
   確認の列挙(`FR-env-03` 受入基準14)に出した集合と、実際に削除を試みる集合を一致させる。
2. `destructive_rm <表示名> <コマンド...>` — **削除コマンドを
   `( trap '' INT TERM; "$@" ) >/dev/null 2>&1` のサブシェルで起動する**。
   成功なら `destructive_deleted`、失敗なら `destructive_failed` を呼ぶ。
   **標準出力と標準エラーを捨てる**のは、`docker rm -f` などが削除対象の名前または ID を
   そのまま出力するためである(捨てないと**利用者向けの出力に生の Docker ID が混じる**)。
3. `destructive_deleted <表示名>` / `destructive_failed <表示名>` / `destructive_skipped <表示名>` —
   いずれも内部ヘルパ `_destructive_done` で `_DESTRUCTIVE_PENDING` から当該項目を外し、
   前2者はそれぞれ `_DESTRUCTIVE_DELETED` / `_DESTRUCTIVE_FAILED` に積む。
   **`destructive_skipped` はどちらにも積まない** — 「削除しないと決めたもの」であり、
   意図した結果なので失敗に数えない。
4. `destructive_report` — 「削除した資源」を列挙し、`_DESTRUCTIVE_FAILED` または
   `_DESTRUCTIVE_PENDING` が非空のときだけ「削除できなかった / 未削除のまま残った資源」を
   列挙する。**`_DESTRUCTIVE_PENDING` の項目には `(未着手)` を付ける**。
5. `destructive_arm_interrupt` — `_DESTRUCTIVE_INTERRUPTED=0` に初期化し、
   `trap '_DESTRUCTIVE_INTERRUPTED=1' INT TERM` を仕掛ける。
   **`MODULE-cli-common-lock` が張った `trap '_release_all_locks; exit 130' INT TERM` を上書きする**
   が、`EXIT` の trap は残るのでロックは解放される。
6. `destructive_abort_if_interrupted` — 旗が立っていなければ 0 を返す。立っていれば中断の旨と
   `destructive_report` の内容を stderr へ出して `exit 130` する。
   **呼び出し元は削除の区切りごとにこれを呼ぶ**。

**終了コード 1 の判定はこの機能が行わない。** 呼び出し元が `_DESTRUCTIVE_FAILED` の要素数を見て
決める(`claude-dev:1101` / `:2160`)。`_DESTRUCTIVE_PENDING` は判定に入らないが、
中断の経路は先に 130 で終わるため、**最後まで走りきったときに未着手が残ることはない**。

## 呼び出され方

- 契機: `logout` / `reset` の削除処理からの関数呼び出し。
- 前提条件: **最初の `destructive_rm` より前に** `destructive_arm_interrupt` を1度呼んでいること
  (呼ばないと中断の遅延が成立せず、`MODULE-cli-common-lock` の即時 130 のままになる)。
  **`destructive_plan` はそれより前でよい**(現行の呼び出し元は対象を出そろえてから `arm_interrupt` する)。
- 引数: 表示名(利用者に見せる資源の名前)と、`destructive_rm` の場合は削除コマンドの語列。
  **表示名の書式は本機能が定めない**(呼び出し元が組み立てる)。
- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

`callees` は「なし」。この機能は Docker とホストの状態を直接触らず、
**渡されたコマンドを起動して結果を記録するだけ**である。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `destructive_rm` は**成否によらず 0 を返す**(`set -e` の下で呼び出し元を落とさないため)。`destructive_abort_if_interrupted` は中断要求が無ければ 0、あれば `exit 130` でプロセスを終える。他の6つは記録のみで意味のある戻り値を持たない |
| 永続化 | **この機能自身は永続化しない。渡された任意のコマンドを起動するだけである。** 現行の呼び出し元が渡すのは、Docker 資源の削除(コンテナ・ネットワーク・ボリューム・イメージ)と、**ホスト側プロジェクト配下の認証ファイルの削除**(`rm -f`。`claude-dev:1065`-`:1068` / `claude-dev-mac:1133`-`:1136`)である。**共有ボリューム `claude-dev-auth` の中身の消去はこの機能を通らない** — `logout` が専用の一時コンテナを直接起動し、結果だけを `destructive_deleted` / `_failed` / `_skipped` に記録する(`claude-dev:1077`-`:1095`)。どの資源を渡すかは `MODULE-cli-logout` / `MODULE-cli-reset` が決める |
| 発火するイベント | なし |
| ログ | `destructive_report` が「削除した資源」「削除できなかった / 未削除のまま残った資源」を1行ずつ出す。中断時は `destructive_abort_if_interrupted` が中断の旨とあわせて stderr へ出す |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| **`destructive_rm` の削除コマンドが非0で終わった** | `destructive_failed` を呼び、**`destructive_rm` 自身は 0 を返す** | 呼び出し元は `set -e` で落ちない。失敗は `_DESTRUCTIVE_FAILED` の要素数で判定する(**戻り値では判定できない**) |
| **削除の実行中に `INT` / `TERM` を受けた** | サブシェルが `trap '' INT TERM` を張っているので**進行中の1件は最後まで走る**。旗だけが立つ | 次の `destructive_abort_if_interrupted` で 130 になる(`FR-env-03` 受入基準23) |
| **`destructive_abort_if_interrupted` を最後の削除の後に置かなかった** | 旗が立っていても再検査が無いため 130 にならず、呼び出し元の結果表示を経て 0 または 1 で終わる | 中断したのに成功の文言が出る。**呼び出し元は最後の削除の直後にも検査点を置く** |
| **`destructive_plan` した資源に対して `deleted` / `failed` / `skipped` のどれも呼ばれなかった** | `_DESTRUCTIVE_PENDING` に残り、`destructive_report` が `(未着手)` として列挙する | 終了コードには効かない(判定は `_DESTRUCTIVE_FAILED` だけを見る)ため、**表示だけが残る** |
| 端末で `Ctrl-C` を押した(非対話シェル) | 子プロセスがシェルと同じプロセスグループに入るため `docker` にも SIGINT が直接届くが、`trap ''` が設定する `SIG_IGN` は `exec` した子へ継承されるので `docker` はそれを無視して削除を完了する | 「進行中の1件を終えてから中断する」が両 OS で成立する |

## 実装上の判断

- [DS-05] 8関数を1機能へ統合して昇格させ、`_destructive_done` は入口にしない — 理由: 4つのモジュール水準変数を共有する1つの手順であり、個別に昇格させると状態の持ち主が分散して「どれを先に呼ぶか」が読めなくなる。`_destructive_done` は `deleted` / `failed` / `skipped` からのみ呼ばれるグループ内部のヘルパである / 見直す条件: どれかの入口が他の7つと状態を共有しなくなったとき
- [D0-scope-02] 削除の成否を**1件ごとに記録**し、最後にまとめて判定する(1件目の失敗で止めない) — 理由: 途中で止めると、より中途半端な状態が残る。**決定 `D0-env-08` 項5 が定める「失敗を握りつぶさない」を、止めずに満たす形がこれである**(項5 は結果を要求するだけで、記録の持ち方は実装内部の構造であり `D0-scope-02` の委任に入る) / 見直す条件: `D0-env-08` 項5 が「最初の失敗で中止する」へ変わったとき
- [DS-02] `destructive_rm` を**成否によらず 0 を返す**形にする — 理由: 既存の呼び出し元がすべて素の呼び出しであり、非0を返すと `set -e` がその場でスクリプトを落として残りの片付けが行われない。**代償として `&&` で繋いだ判定が使えない**ので、呼び出し元は `_DESTRUCTIVE_DELETED` の要素数の増減で判定する / 見直す条件: 呼び出し元が `|| true` を伴う形に揃ったとき
- [DS-02] 削除コマンドを `( trap '' INT TERM; ... )` のサブシェルで起動する — 理由: 非対話シェルではジョブ制御が無効で子プロセスがシェルと同じプロセスグループに入るため、`Ctrl-C` が `docker` へ直接届き「進行中の1件を終えてから中断する」が成立しない。`SIG_IGN` は `exec` した子へ継承されるのでこの形で成立し、`setsid` と違って macOS でも同じに書ける / 見直す条件: 対話シェルでのみ実行される形に変わったとき
- [DS-03] `destructive_rm` が削除コマンドの標準出力と標準エラーを捨てる — 理由: `docker rm -f` / `docker network rm` / `docker volume rm` / `docker rmi` は削除した対象の名前または ID をそのまま出力するため、捨てないと利用者向けの出力に生の Docker ID が混じる / 見直す条件: 削除コマンドの出力に利用者が読む価値のある情報が入るようになったとき
- [DS-02] `_DESTRUCTIVE_PENDING` の残りを終了コードの判定に入れない — **観測される終了コードそのものは `FR-env-03-18`(消えなかった資源が1件以上なら 1)と同23(中断は 130)が定めており、この行が決めているのは「その要件をどう内部で判定するか」だけである**。理由: 最後まで走りきった場合は全項目が deleted / failed / skipped のいずれかに落ちるため、未着手が残るのは中断の経路だけであり、その経路は先に 130 で終わる。判定に入れると中断時に 130 と 1 のどちらで終わるかが順序に依存する / 見直す条件: 中断以外で未着手が残る経路ができたとき
- [D0-scope-03] Linux 版・macOS 版の両方に同じ形で置く — 理由: 同じサブコマンドの成否と出力を OS で変えないため / 見直す条件: 片方の OS でしか成立しない実装手段が必要になったとき

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| **`destructive_rm` の戻り値では削除の成否が分からない** | 呼び出し元は `_DESTRUCTIVE_DELETED` の要素数で判定する必要があり、素直に `&&` で繋ぐと失敗した資源まで「削除しました」の列挙に入る | なし(閾値の外: 実装上の判断3 が代償として明示的に受け入れたもの) |
| **中断の検査点の位置は呼び出し元まかせである** | 最後の削除の後に `destructive_abort_if_interrupted` を置き忘れると、中断したのに成功の文言が出て 0 または 1 で終わる | なし(閾値の外: `MODULE-cli-logout` 手順12 と `MODULE-cli-reset` 手順10 が置き場所を持つ) |
| **`stop` はこの手順を使わない** | 同じ「削除」でも `stop` の失敗の扱い(握って続行)は本機能と別実装になる | なし(閾値の外: `D0-env-08` 項5 が `stop` を例外として明示している) |
