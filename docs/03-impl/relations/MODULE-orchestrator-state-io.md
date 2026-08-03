---
id: MODULE-orchestrator-state-io
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/state.go::readJSON, orchestrator/state.go::writeAtomic, orchestrator/state.go::writeJSONAtomic, orchestrator/state.go::appendJSONL
callers: MODULE-orchestrator-mode, MODULE-orchestrator-state, MODULE-orchestrator-state-intervention
callees: なし
contracts: なし
design: DSN-mod-01
requirements: FR-orch-05
tests: orchestrator/state_test.go::TestStateRoundTrip, orchestrator/state_test.go::TestAuditAppend, orchestrator/state_test.go::TestSidecarRoundTrip
updated: 2026-08-02
summary: JSON の読み書きを一時ファイル経由の原子的置換で行う
---

# MODULE-orchestrator-state-io 原子的な永続化プリミティブ

## 目的

書き込み途中でプロセスが落ちても状態ファイルが壊れないようにする(FR-orch-05)。中断からの
復旧が成立する前提はこの機能が担保している。

## 処理の流れ

1. `readJSON(path, v)`: ファイルを読み JSON をデコードする。
2. `writeAtomic(path, data)`: 同じディレクトリに一時ファイルを作って書き込み、`os.Rename` で
   目的のパスへ置き換える(同一ファイルシステム内の rename は原子的)。
3. `writeJSONAtomic(path, v)`: `v` をエンコードして `writeAtomic` に渡す。
4. `appendJSONL(path, v)`: 1行 JSON を追記モードで書き足す(監査・仮定・介入の追記型ログ用)。

## 呼び出され方

- 契機: `MODULE-orchestrator-state` / `MODULE-orchestrator-state-intervention` /
  `MODULE-orchestrator-mode` が永続化するとき。
- 前提条件: 対象ディレクトリが存在し書き込み可能であること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `path` | パス | 必須 | 書き込み先。一時ファイルは同じディレクトリに作る |
| `v` | 任意の構造体 | 必須 | `encoding/json` でエンコードできること |

- 認可: プロセス内呼び出し。

## 連携先と連携内容

連携先なし(標準ライブラリのみを使う)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | エラー(成功時は nil) |
| 永続化 | 呼び出し元が指定したファイル。`writeAtomic` は一時ファイルを作って rename する。`appendJSONL` は追記のみ |
| 発火するイベント | なし |
| ログ | なし |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 一時ファイルを作れない | エラーを返し、目的のファイルは無傷のまま | 呼び出し元がエラーを伝播する |
| `os.Rename` が失敗する | エラーを返す。一時ファイルが残ることがある | 状態は前の内容のまま |
| ファイルが存在しない(`readJSON`) | `os.ErrNotExist` を返す | 呼び出し元が「未作成」として扱う |
| JSON が壊れている(`readJSON`) | デコードエラーを返す | 呼び出し元が新規扱いに倒す |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 一時ファイルを同じディレクトリに作る(別ファイルシステムをまたぐと `os.Rename` が原子的でなくなるため) | D0-orch-03 |
| 2 | 追記型ログだけは原子的置換を使わない(追記の単位が1行で、途中で落ちても既存行は壊れないため) | D0-orch-03 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `fsync` を行わない | OS クラッシュ時に直近の書き込みが失われうる(プロセスクラッシュには耐える) | なし |
