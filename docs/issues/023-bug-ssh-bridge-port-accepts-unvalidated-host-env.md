---
id: 023-bug-ssh-bridge-port-accepts-unvalidated-host-env
type: bug
severity: 中
found: 2026-08-03
found_in: /doc-check task-impl-depth(反復3。留保した判定根拠をコードで裏取りして発見)
related: CTR-cli-container, MODULE-cli-start, FR-env-04, FR-env-10, D0-scope-07
summary: CLAUDE_DEV_SSH_BRIDGE_PORT はホスト環境変数から無検証で採られ、不正値でも「SSH agent 転送」を成功として表示する
---

## 事象

`claude-dev-mac` の `ensure_ssh_bridge()` は、ブリッジのポートを**ホストの環境変数から読む**。

```sh
# claude-dev-mac:274
local port="${CLAUDE_DEV_SSH_BRIDGE_PORT:-}"
[ -n "$port" ] || port=$(find_free_local_port)
nohup socat "TCP-LISTEN:${port},bind=127.0.0.1,fork,reuseaddr" "UNIX-CONNECT:${sock}" >/dev/null 2>&1 &
echo $! > "$bpid"
echo "$port" > "$bport"
echo "$port"
```

したがって利用者が `export CLAUDE_DEV_SSH_BRIDGE_PORT=foo`(あるいは `0` / `99999` / 空白入り)
を設定した状態で `claude-dev start` を実行すると、その値が**検証されずに** `socat` の
`TCP-LISTEN:` へ渡る。`socat` は失敗するが `>/dev/null 2>&1 &` で出力が捨てられ、
`$!` はバックグラウンドプロセスの PID なので `echo $! > "$bpid"` は成功する。

結果として `claude-dev-mac:899` 以降が実行され、端末には

```
🔑 SSH agent 転送: 127.0.0.1:foo（専用 agent [<name>]、鍵 N 件 / <source>）
```

と**成功したかのように表示される**。コンテナ側 `scripts/entrypoint-claude.sh:96`〜`:98` も
`TCP:host.docker.internal:${CLAUDE_DEV_SSH_BRIDGE_PORT}` へ socat を張ろうとして静かに失敗する。
利用者は SSH agent 転送が効いていないことに気づけず、`git push` などが失敗して初めて分かる。

生存判定(`kill -0 "$(cat "$bpid")"`)は**次回の起動時**にしか走らないため、初回は必ず成功表示になる。

## 影響

- 対象は macOS 経路(`claude-dev-mac`)のみ。Linux 経路にはこの環境変数がない。
- 秘密は漏れない(鍵は専用 agent に留まり、TCP は `127.0.0.1` に bind される)。
  データも壊れない。**被害は「利用者が失敗に気づけない」ことに限られる**ため severity は「中」。
- 誤設定が必要なので通常運用では起きない。ただし `CLAUDE_DEV_*` は他にも利用者が
  設定する変数があり(`CLAUDE_DEV_NO_ATTACH` など)、取り違えは起こりうる。

## 原因の見当

`CLAUDE_DEV_SSH_BRIDGE_PORT` は**コンテナへ渡す**ための変数として設計され(`CTR-cli-container`)、
ホスト側の入力として読む経路が後から足されたため検証が付かなかった、という**推測**。
`find_free_local_port()` のフォールバックがあるので、「値は常に CLI が生成する」という
前提が書かれたままになっている。

## 正はどちらか

**実装が誤り**(ドキュメントは実装を正しく写していたが、留保の判定根拠が事実に反していた)。

`docs/03-impl/contracts/cli-container.md` の「既知の制限」は
`CLAUDE_DEV_SSH_BRIDGE_PORT` を検証しないことを**起票の閾値の外**と判定し、その根拠を
「値は CLI が生成して渡すため利用者が誤った値を与える経路が無い」と書いている。
上のとおり**この根拠は成立しない**(ホスト環境変数の経路がある)。
`D0-scope-07` の閾値 (a)「利用者が失敗に気づけない」に該当し、(b) この被害を説明する issue も
無かったため、**起票が正しい扱い**である。

## 対処案

| 案 | 内容 |
|---|---|
| A | `ensure_ssh_bridge()` で `CLAUDE_DEV_SSH_BRIDGE_PORT` を `1〜65535` の整数として検証し、外れていれば警告して `find_free_local_port()` にフォールバックする(**推奨**。振る舞いの後退が無い) |
| B | `socat` の起動可否を確認してから成功表示する(`kill -0` を初回にも行う)。A と併せると誤設定以外の失敗も拾える |
| C | ホスト環境変数からの読み取りを廃止し、常に `find_free_local_port()` を使う(デバッグ用途の口を失う) |

いずれの案でも、`docs/03-impl/contracts/cli-container.md` の「既知の制限」の**判定根拠は
差し替えが必要**である(現在の根拠は事実に反している)。
