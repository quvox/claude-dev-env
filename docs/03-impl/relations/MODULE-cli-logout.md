---
id: MODULE-cli-logout
module: MOD-cli-logout
kind: tool
sync: sync
impl: claude-dev::main#logout, claude-dev-mac::main#logout
callers: なし
callees: MODULE-cli-common-container-exists, MODULE-cli-common-require-setup
contracts: なし
design: DSN-mod-01, DSN-mod-02, DSN-auth-01
requirements: FR-env-03
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-04
summary: Claude と Codex の認証情報を共有ボリュームごと削除する
---

# MODULE-cli-logout 認証の削除

## 目的

共有ボリュームに残っている認証を消し、以後のコンテナが未ログイン状態で起動するようにする
(FR-env-03)。claude と codex の認証が同じボリュームに同居しているため、両方が同時に消える。

## 処理の流れ

1. `MODULE-cli-common-require-setup` でイメージをそろえる。
2. 稼働中の Claude コンテナと docker-proxy コンテナを `docker rm -f` で削除する
   (`MODULE-cli-common-container-exists` で存在を確認してから消す)。
3. `claude-dev-auth` をマウントした一時コンテナで `rm -rf /auth/* /auth/.*` を実行し、
   ボリュームの中身を空にする。

## 呼び出され方

- 契機: 利用者が `claude-dev logout` を実行したとき。
- 前提条件: なし。
- 引数: なし。

| 引数 | 型 | 必須 | 制約 | 実装が行う検証 |
|---|---|---|---|---|
| (なし) | - | - | 位置引数を渡しても**すべて無視する** | **検証しない**(引数を取らないため。対象はホスト上の全 claude-dev コンテナで固定) |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-require-setup

- 何のために呼ぶか: 削除用の一時コンテナに使うイメージを保証するため。
- 何を渡すか: なし。
- 何を受け取るか: なし。
- **失敗したときどうなるか**: `set -e` で非0終了し、認証は消えない。

### MODULE-cli-common-container-exists

- 何のために呼ぶか: 削除対象のコンテナ(停止中を含む)を特定するため。
- 何を渡すか: コンテナ名。
- 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: 「存在しない」と判定され、削除がスキップされる。残骸が残るが後続の
  `rm -rf` は共有ボリュームを空にするので認証は消える。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0(削除に失敗しても 0。失敗はすべて握る) |
| 永続化 | 共有ボリューム `claude-dev-auth` の中身(claude の `.credentials.json` / `.claude.json` と codex の `codex/auth.json`)を削除する。**あわせて全 Claude コンテナと docker-proxy コンテナを削除する** |
| 発火するイベント | なし |
| ログ | 標準出力へ削除結果 |

### 破壊の範囲と順序

**確認プロンプトは無い。** 実行すると即座に次の順で進む。

1. `require_setup`(イメージが無ければビルド。**ここだけは `set -e` で失敗すると中止**する)
2. **イメージから逆引きした全 Claude コンテナ**(稼働中・停止中の両方、**プロジェクトを問わない**)を
   `docker rm -f`
3. docker-proxy コンテナを削除
4. 一時コンテナで `rm -rf /auth/* /auth/.*` を実行し、共有ボリュームの中身を空にする

**手順 2 の対象はホスト上のすべての claude-dev コンテナ**であり、カレントディレクトリの
セッションだけではない。

### 並行性

**排他機構を持たない。**

| 同時に起きること | 実際の結果 |
|---|---|
| 他プロジェクトのセッションが稼働中 | **確認せずに削除する。** 作業中のセッションが落ちる |
| `logout` と `start` | 保護は無い。`start` の認証コピー(手順4)と重なると、**認証が空のまま起動する**(未ログイン状態) |
| `logout` と `login` / `login-codex` | 保護は無い。ログイン直後の認証が消える、またはログインが書いた直後に空になる |
| `logout` を2つ同時 | 双方が同じ対象を消す。すべての削除が失敗を握るため、どちらも 0 で終わる |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 稼働中コンテナがある | **確認なしで** `rm -f` して強制削除してから認証を消す | 利用者のセッションが切れる |
| ボリュームが存在しない | `docker run` がボリュームを自動作成し、空のまま終わる | なし |
| イメージが無い | `require_setup` がビルドする。ビルドに失敗すると `set -e` で非0終了し、**認証は消えない** | 利用者はイメージを用意する |
| 一時コンテナの `rm -rf` が失敗した | `2>/dev/null \|\| true` で握り、**「認証情報を削除しました」と表示して 0 で終わる** | 認証が残っているのに消えたと表示される |
| `/auth` 直下に隠しディレクトリがある | `rm -rf /auth/* /auth/.*` は `.` と `..` にも当たるためエラーを出すが握られる。**通常のファイル・ディレクトリは消える** | なし |
| プロジェクト配下にコピー済みの認証(`${PROJECT_DIR}/.claude/` `.codex/`) | **削除対象に含まれない** | 次回 `start` で共有ボリューム側が空でも、プロジェクト側の古い認証はそのまま残る |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | claude と codex を個別に消す分岐を作らない(同一ボリュームに同居させた D0-auth-01 の帰結) | D0-auth-01 |
| 2 | 削除の失敗をすべて握る(片付けの途中で止めない) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| codex だけ・claude だけのログアウトができない | 片方だけ消したい場合は手作業になる | なし(閾値の外: **`D0-auth-01` がそう決めた帰結**) |
| 確認プロンプトが無く、全プロジェクトのコンテナを落とす | 他プロジェクトで作業中でも巻き込む(`reset` は確認するのに `logout` はしない) | `docs/issues/029-modify-logout-kills-all-projects-without-confirmation.md` |
| プロジェクト配下の認証コピーを消さない | ログアウトしたつもりでもプロジェクト側の認証が残る | `docs/issues/025-modify-logout-and-reset-report-success-without-deleting.md` |
| 削除の失敗を握って「削除しました」と表示する | 認証が残っていることに気づけない | `docs/issues/025-modify-logout-and-reset-report-success-without-deleting.md` |
