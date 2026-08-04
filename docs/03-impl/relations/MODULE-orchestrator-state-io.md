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
updated: 2026-08-04
summary: JSON の読み書きを一時ファイル経由の原子的置換で行う
---

# MODULE-orchestrator-state-io 原子的な永続化プリミティブ

## 目的

書き込み途中でプロセスが落ちても状態ファイルが壊れないようにする(FR-orch-05)。中断からの
復旧が成立する前提はこの機能が担保している。

## 処理の流れ

1. `readJSON(path, v)`: ファイル全体を読み、`encoding/json` でデコードする。**部分読み・
   ストリーム読みはしない。**
2. `writeAtomic(path, data)`:
   ① 親ディレクトリを `MkdirAll`(0755)で作る → ② **同じディレクトリ**に `.tmp-*` の一時ファイルを
   作る → ③ 書き込む → ④ **`Sync()` でファイル本体を fsync する** → ⑤ `Close()` →
   ⑥ `os.Rename` で目的のパスへ置き換える。③④⑤ のどこで失敗しても**一時ファイルを削除してから**
   エラーを返す(目的のファイルは無傷)。
3. `writeJSONAtomic(path, v)`: `MarshalIndent`(2スペース)+ 末尾改行にして `writeAtomic` へ渡す。
4. `appendJSONL(path, v)`: 親ディレクトリを作り、1行 JSON(末尾改行)を
   `O_APPEND|O_CREATE|O_WRONLY`(0644)で**1回の `Write`** で書き足す。**fsync しない。**

**原子性の境界はこう決まっている**:

| 単位 | 原子的か | 根拠 |
|---|---|---|
| 1ファイルの**置換** | **原子的**(同一ファイルシステム内の rename) | `writeAtomic` |
| 1行の**追記** | **原子的ではない**。1回の `write(2)` で書くため通常は分割されないが、保証は無い | `appendJSONL` |
| **複数ファイルにまたがる更新** | **原子的ではない。トランザクションは存在しない** | `SavePlan` / `SaveState` / `SaveControl` / `appendJSONL` はそれぞれ独立の呼び出し |
| ディレクトリエントリの永続化 | **保証しない**(ファイル本体は fsync するが、**ディレクトリの fsync は行わない**) | `writeAtomic` に親ディレクトリの `Sync` が無い |

## 呼び出され方

- 契機: `MODULE-orchestrator-state` / `MODULE-orchestrator-state-intervention` /
  `MODULE-orchestrator-mode` が永続化するとき。
- 前提条件: 対象ディレクトリが存在し書き込み可能であること。
- 引数:

| 引数 | 型 | 必須 | 制約 | 実装が行う検証 |
|---|---|---|---|---|
| `path` | パス | 必須 | 書き込み先。一時ファイルは同じディレクトリに作る | **検証しない**。パスは呼び出し元(Store)が組み立てる。`v` が JSON 化できなければ `Marshal` のエラーを返す |
| `v` | 任意の構造体 | 必須 | `encoding/json` でエンコードできること | 同上 |

- 認可: プロセス内呼び出し。

## 連携先と連携内容

連携先なし(標準ライブラリのみを使う)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | エラー(成功時は nil)。`readJSON` は `os.ErrNotExist` をそのまま返す |
| 永続化 | 呼び出し元が指定したファイル。`writeAtomic` は同じディレクトリに `.tmp-*` を作って rename する。`appendJSONL` は追記のみ。**いずれも親ディレクトリを 0755 で、追記ファイルを 0644 で作る** |
| 発火するイベント | なし |
| ログ | なし |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 一時ファイルを作れない | エラーを返し、目的のファイルは無傷のまま | 呼び出し元がエラーを伝播する |
| 書き込み / `Sync` / `Close` が失敗した | **一時ファイルを削除してから**エラーを返す。目的のファイルは無傷 | 状態は前の内容のまま |
| `os.Rename` が失敗する | エラーを返す。**この経路だけは一時ファイルが残る**(`.tmp-*` が溜まる) | 状態は前の内容のまま |
| プロセスが `Write` と `Rename` の間で死んだ | 目的のファイルは前の内容のまま。`.tmp-*` が残る | 再開時に前の状態から続く |
| **OS がクラッシュした** | ファイル本体は fsync 済みだが**ディレクトリエントリは fsync していない**ため、rename が失われて前の内容に戻ることがありうる | 直近1回の更新が消えた状態で再開する |
| `appendJSONL` の途中でプロセスが死んだ | **部分行が残りうる**。以後の追記はその後ろに続くため、**壊れた行が1行残ったまま**になる | 行単位で読む側が壊れた行を捨てる必要がある |
| ファイルが存在しない(`readJSON`) | `os.ErrNotExist` を返す | 呼び出し元が「未作成」として扱う |
| JSON が壊れている(`readJSON`) | デコードエラーを返す | 呼び出し元が新規扱いに倒す(`LoadControl` の呼び出し元は削除もする) |
| 複数のプロセス / goroutine が同じパスへ同時に書く | **排他しない**。`writeAtomic` は最後の rename が勝ち、途中の混在は起きない。`appendJSONL` は行が交互に混ざる | 呼び出し元(`MODULE-orchestrator-controller`)がロックで直列化している範囲でのみ整合する |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 一時ファイルを同じディレクトリに作る(別ファイルシステムをまたぐと `os.Rename` が原子的でなくなるため) | D0-orch-03 |
| 2 | 追記型ログだけは原子的置換を使わない(追記の単位が1行で、途中で落ちても既存行は壊れないため) | D0-orch-03 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| ディレクトリの `fsync` を行わない | OS クラッシュ時に rename 自体が失われうる(プロセスクラッシュには耐える) | なし(閾値の外: **`FR-orch-05` 受入基準6 が「原子的置換または追記のみ」を要件として定めており**、OS クラッシュ時の1回分の喪失はその範囲内) |
| `appendJSONL` が fsync せず、書き込みの原子性も保証されない | プロセス異常終了で部分行が残りうる | なし(閾値の外: **`FR-orch-05` 受入基準9 が部分行の残存を要件として許容している**) |
| **複数ファイルにまたがるトランザクションが無い** | `plan.json` と `state.json` が食い違う瞬間が存在する。復旧は「plan が正」という規約で吸収している | なし(閾値の外: **`FR-orch-05` 受入基準8 が1ファイル1書き込みを一貫性の境界として定めている**) |
| `os.Rename` 失敗時の `.tmp-*` を掃除しない | 失敗が続くと `.orchestrator/` に一時ファイルが溜まる | `docs/issues/026-modify-controller-swallows-state-save-failures.md`(呼び出し元が失敗を握るため誰も気づけない) |
| ファイルロックを持たない | 同じ store を2つのコントローラが触ると、後勝ちで上書きされる(**検出も警告も無い**) | `docs/issues/021-modify-orchestrator-store-has-no-lock.md` |
