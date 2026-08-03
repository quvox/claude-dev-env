---
id: MODULE-vm-mode-healthd
module: MOD-vm-mode
kind: tool
sync: sync
impl: scripts/vm-healthd.sh::main#--loop, scripts/vm-healthd.sh::main
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-03, DSN-arch-01
requirements: FR-env-08, NFR-ops-01
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する。静的検証として `bash -n` は緑)
updated: 2026-08-02
summary: QEMU の CPU 使用率から資源逼迫を検知し tmux と health へ書く
---

# MODULE-vm-mode-healthd VM の資源逼迫監視

## 目的

ゲストの RAM 逼迫(スラッシング)に人間が気づけるようにする(FR-env-08・NFR-ops-01)。
スラッシング中はゲストの ssh も docker も応答しないため、**claude コンテナ側から見える QEMU
プロセスの CPU 使用率だけ**で判定するのがこの機能の要点である。

## 処理の流れ

1. `evaluate_once`: pidfile から QEMU の pid を得る(無ければ `STATE=OFF` を書いて終わる)。
2. `/proc/<pid>/stat` の `utime + stime` を `VM_HEALTH_INTERVAL`(既定15秒)間隔で2点サンプルし、
   `getconf CLK_TCK` を使って1コア基準の CPU% を算出する。
3. 上限 `CEIL` は `/proc/<pid>/cmdline` から解決した `-smp N` × 100% とする。比率 = CPU% ÷ CEIL。
4. **判定**: 比率が `VM_HEALTH_CPU_PCT`(既定60)以上を「hot」とし、`VM_HEALTH_SUSTAIN`
   (既定12回 ≒ 3分)連続で hot なら `WARN` にする。hot が途切れれば OK に戻す。
   低めの閾値と長めの窓を組み合わせ、一過性のビルドを除外しつつスラッシングを捕まえる。
5. **health ファイル**: `${VM_HOME}/health` を毎周回アトミックに上書きする
   (`STATE` / `CPU` / `CEIL` / `TS` / `MSG`)。
6. **tmux 連携**: WARN の間は `tmux set -g @vm_health "⚠ VM資源逼迫…"`、OK へ戻ったら `set -gu` で
   クリアする。OK → WARN の遷移時、または `VM_HEALTH_COOLDOWN`(既定600秒)が経過したときだけ
   `display-message` でフラッシュする。tmux サーバが起動していない(`has-session` が失敗する)ときは
   各操作をスキップする。

## 呼び出され方

- 契機: `MODULE-vm-mode-up` が dockerd の準備完了後に `--loop` で常駐起動する。
- 前提条件: QEMU が pidfile 付きで動いていること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `--loop` | フラグ | 任意 | 常駐する。省略時は一度評価して終わる |
| `VM_HEALTH_INTERVAL` / `_CPU_PCT` / `_SUSTAIN` / `_COOLDOWN` | 環境変数 | 任意 | 既定 15 / 60 / 12 / 600 |

- 認可: コンテナ内のユーザ。

## 連携先と連携内容

連携先なし(`tmux` の実行は外部コマンド呼び出し)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0。`--loop` は終了しない |
| 永続化 | **`${HOME}/.claude-dev-vm/health`**(`STATE` / `CPU` / `CEIL` / `TS` / `MSG` を tmp → rename でアトミック上書き)。**この書式をこの機能が決め、`MODULE-vm-mode-cli` の `vm status` と `MODULE-orchestrator-dashboard` の VM バナーが読んで依存する**(鮮度は `TS` で判定する)。tmux ユーザ変数 `@vm_health` |
| 発火するイベント | tmux の `display-message` によるフラッシュ通知 |
| ログ | `${HOME}/.claude-dev-vm/logs/vm-healthd.log` |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| QEMU が動いていない | `STATE=OFF` を書いて終わる | `vm status` が停止として表示する |
| tmux サーバが起動していない | `has-session` の失敗を見て各 tmux 操作をスキップする | バナーは出ないが health ファイルは更新される |
| 一過性の高負荷(ビルド等) | `VM_HEALTH_SUSTAIN` 連続で hot にならなければ WARN にしない | 誤警告が出ない |
| health ファイルが古い | 読む側(`vm status` / ダッシュボード)が `TS` で鮮度を判定して無視する | 古い警告が残らない |
| 一時的な `/proc` 読み取り失敗 | `set -u` のみで `-e` を付けていないためループは止まらない | 次の周回で再評価する |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | ゲストへ問い合わせず、ホスト側(claude コンテナ側)から見える QEMU の CPU だけで判定する(スラッシング中はゲストが応答しないため) | D0-scope-04 |
| 2 | サンプリング窓をループ周期と兼ねる(`sleep INTERVAL` を評価の内側に含める) | D0-scope-04 |
| 3 | 低め閾値(60%)+ 長め窓(3分)にする(一過性ビルドを除外しつつスラッシングを捕まえる) | D0-scope-04 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| CPU 使用率からの間接推定 | RAM 逼迫以外の理由による高負荷も WARN になりうる | なし |
| `VM_HEALTH_*` は環境変数の上書きのみ | CLI からの明示的な受け渡し口が無い(既定値運用) | なし |
