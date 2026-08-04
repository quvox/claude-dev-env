---
id: MODULE-cli-reset
module: MOD-cli-reset
kind: tool
sync: sync
impl: claude-dev::main#reset, claude-dev-mac::main#reset
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-01, FR-env-03
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-04
summary: コンテナ・ボリューム・イメージを全削除して初期状態へ戻す
---

# MODULE-cli-reset 全リセット

## 目的

環境を作り直したいときに、本システムが作った Docker 資源をまとめて消す(FR-env-01)。
認証も共有ボリュームごと消える(FR-env-03)。

## 処理の流れ

1. 削除対象を列挙して表示し、確認プロンプトを出す(同意しなければ何もしない)。
2. 全 Claude コンテナ・全 `fwd-*` コンテナ・`claude-dev-docker-proxy` を `docker rm -f` する。
3. 共有ボリューム `claude-dev-auth` / `claude-dev-history` / `claude-dev-config` と、
   `claude-dev-chrome-*` をすべて削除する。
4. docker network `claude-dev-net` を削除する。
5. イメージ `claude-dev-claude` / `claude-dev-claude-vnc` / `claude-dev-docker-proxy` を削除する。

## 呼び出され方

- 契機: 利用者が `claude-dev reset` を実行したとき。
- 前提条件: なし。**対象を絞る引数は無く、常にホスト全体の claude-dev 資源が対象**である
  (カレントディレクトリは関係しない)。
- 引数: なし。

| 引数 | 型 | 必須 | 制約 | 実装が行う検証 |
|---|---|---|---|---|
| (なし) | - | - | 位置引数を渡しても**すべて無視する** | **検証しない**(引数を取らない)。唯一の入力は確認プロンプトの1文字で、`y` / `Y` 以外はすべてキャンセル |

**確認プロンプトが受理する入力**(`read -p "実行しますか？ (y/N) " -n 1 -r`。**1文字だけ**読む):

| 入力 | 結果 |
|---|---|
| `y` / `Y` | 削除を実行する |
| それ以外の1文字(`n` / Enter / 空 / 任意の文字) | 「キャンセルしました」と表示して `exit 0`。**何も削除しない** |
| **非 TTY(標準入力がパイプ・リダイレクト)** | `read` が即座に空を返すため**キャンセル扱い**になる。`yes y \| claude-dev reset` のように `y` を流し込めば実行される |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

連携先なし(削除処理を本分岐が直接書いており、共有関数を呼んでいない)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0(同意しなかった場合も、一部の削除に失敗した場合も 0) |
| 永続化 | **破壊的**: 全 Claude コンテナ・`fwd-*`・`claude-dev-docker-proxy` の削除、docker volume `claude-dev-auth` / `claude-dev-history` / `claude-dev-config` / `claude-dev-chrome-*` の削除、docker network `claude-dev-net` の削除、3イメージの削除 |
| 発火するイベント | なし |
| ログ | 標準出力へ削除対象の一覧と結果 |

### 並行性

**排他機構を持たない。同意した時点以降、他プロジェクトが稼働中かどうかを確認しない。**
削除は次の順で行い、**各ステップは失敗を握って次へ進む**。

1. 全 Claude コンテナ(イメージから逆引き)と全 `fwd-*` コンテナ → 2. docker-proxy →
3. 共有ボリューム3本と `claude-dev-chrome-*` → 4. `claude-dev-net` → 5. イメージ3本

| 同時に起きること | 実際の結果 |
|---|---|
| 他プロジェクトのコンテナが稼働中 | **確認せずに削除する。** 他の利用中セッションが落ちる(表示される確認文にも「全 Claude Code コンテナ」と明示されている) |
| `reset` と `start` | 保護は無い。`start` が先行していると、認証コピー済みのコンテナが直後に消される。逆順なら `start` が新しい資源を作り直す |
| `reset` と `login` / `login-codex` | 保護は無い。ログイン直後の認証がボリュームごと消える |
| `reset` を2つ同時 | 双方が同じ対象を消そうとする。**失敗はすべて握る**ため、どちらも 0 で終わる |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 確認プロンプトで同意しない | 何も削除せずに `exit 0` | なし |
| 標準入力が TTY でない | 空入力として扱い**キャンセル**する | 自動実行では削除されない(意図的に `y` を流し込む必要がある) |
| 一部の削除が失敗する(使用中など) | 失敗を握りつぶして次へ進み、最後に「全リセット完了」と表示する。**失敗した項目は表示されない** | 残骸が残るのに完了と表示される |
| VM モードのボリューム `claude-dev-vm-<name>` | **削除対象に含まれない** | ゲストディスクは残る |
| macOS の専用 agent / ブリッジ | **削除対象に含まれない**(掃除は `ssh-keys reset` が担う) | 残骸が残る |
| プロジェクト側の `.claude/` `.codex/` `.claude-dev.yaml` | **削除対象に含まれない**(利用者のリポジトリを触らない) | 認証ファイルのコピーはプロジェクト配下に残る |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 破壊的操作なので確認プロンプトを必須にする | D0-scope-02 |
| 2 | プロジェクト側の `.claude/` `.codex/` `.claude-dev.yaml` は消さない(利用者のリポジトリを触らない) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| VM ボリュームと macOS の agent 残骸を消さない | 完全な初期化にはならない | なし(閾値の外: 表示される削除対象の一覧に含まれておらず、消えないことは事前に読み取れる) |
| 稼働中の他プロジェクトを確認しない | 作業中のセッションを巻き込んで落とす | `docs/issues/020-modify-cli-destructive-commands-have-no-mutual-exclusion.md` |
| 削除の失敗を握って「完了」と表示する | 残骸に気づけない | `docs/issues/025-modify-logout-and-reset-report-success-without-deleting.md` |
| プロジェクト配下にコピーされた認証(`.claude/` `.codex/`)は消えない | `reset` 後も古い認証がプロジェクト側に残る | `docs/issues/025-modify-logout-and-reset-report-success-without-deleting.md` |
