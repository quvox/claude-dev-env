---
id: 047-bug-reset-leaves-vm-volumes-behind
type: bug
severity: 低
found: 2026-08-04
found_in: task-fix-destructive-scope の /doc-check(3回目)。契約 CTR-cli-container の資源表と MODULE-cli-reset の削除対象を突き合わせた際に確定
related: MODULE-cli-reset, MODULE-makefile-clean, CTR-cli-container, FR-env-01, FR-env-03
summary: reset は「初期状態へ戻す」と説明しながら VM モードのボリューム `claude-dev-vm-<name>` を削除しないため、`--vm` を使ったあとの reset では孤児ボリュームがディスクを占有したまま残る
---

## 事象

`claude-dev reset` は共有ボリューム3本(`claude-dev-auth` / `claude-dev-history` /
`claude-dev-config`)と `claude-dev-chrome-*` を削除するが、**`claude-dev-vm-<コンテナ名>` を
削除しない**。

| 出どころ | 記述 |
|---|---|
| 実装 | `claude-dev:1408` のコメント「ボリューム削除(共有 3 ボリューム + コンテナごとの Chrome プロファイル `claude-dev-chrome-*`)」。`claude-dev-mac:1382` も同じ |
| 03-impl | `MODULE-cli-reset.md` の処理の流れ3 が同じ4種類だけを挙げる |
| 02-design | `CTR-cli-container` の「識別の手段は資源ごとに違う」の表は、本システムの共有ボリュームとして**接頭辞 `claude-dev-vm-` を挙げている** |
| 生成側 | `claude-dev:881` の `VM_OPTS="-e CLAUDE_DEV_VM=1 -v claude-dev-vm-${NAME}:${CHOME}/.claude-dev-vm"` が作る。`claude-dev:36` のコメントも「VM ボリューム `claude-dev-vm-<name>` と同方式」と述べる |

つまり **02 の契約は本システムの資源として認識しているのに、`reset` の削除対象からだけ落ちている**。

再現手順:

1. `/dev/kvm` のあるホストで、任意のディレクトリで `claude-dev start --vm` を実行する。
2. `docker volume ls --filter name=claude-dev-vm-` に当該ボリュームができていることを確認する。
3. `claude-dev reset`(同意して実行)を行う。
4. `docker volume ls --filter name=claude-dev-vm-` を再実行する。**手順2 のボリュームが残っている**
   ことを確認する。「全リセット完了」と表示されるが初期状態には戻っていない。

## 影響

- **`reset` の要約(「コンテナ・ボリューム・イメージを全削除して初期状態へ戻す」)と実際が食い違う。**
  VM モードを使ったことがあるホストでは、reset を繰り返しても VM ボリュームが積み上がる。
- VM のディスクイメージは大きく(`VM_DISK` の既定次第で数十 GB になりうる)、**気づかないまま
  ディスクを占有する**。名前がコンテナ名ごとなので、使ったプロジェクトの数だけ残る。
- 利用者は気づけない: `reset` の出力は成功で、終了コードも 0 である。
- `make clean` も同じ範囲しか消さない(`MODULE-makefile-clean`)。

## 暫定回避

`docker volume ls --filter name=claude-dev-vm- -q | xargs -r docker volume rm` を手で実行する。

## 直すときに考えること

- **これは「削除対象を広げる」変更である。** `docs/issues/029` の反省から、破壊的操作の対象を
  広げる判断は 00 起点で行うべきである(`D0-env-08` 項1 は削除対象の定め方を決めているが、
  VM ボリュームには触れていない)。`D0-env-08` の対象に含めるかどうかから決める。
- `claude-dev-vm-*` は**固定接頭辞を持つので名前で識別できる**(`D0-env-08` 項1 の「名前で
  所有権が読み取れる資源」)。識別の手段は既に契約が持っており、追加の仕組みは要らない。
- `stop` の対象に含めるかは別問題である(`stop` は名前付きボリュームを保持する方針
  = `MODULE-cli-stop` 判断1 / `D0-env-05` 項2)。**`reset` だけの話として扱うのが素直**である。
- `docs/issues/046` と同じく `MODULE-makefile-clean` にも同じ穴がある。あわせて直すのが効率的。

## なぜ task-fix-destructive-scope で直さないか

同タスクの「やらないこと」に **「現行の対象範囲を広げない」** が明記されており
(`logout` の削除対象を `fwd-*` へ広げないのと同じ理由)、削除対象の拡大は範囲外である。
同タスクは「巻き込みを止める」ことだけを行う。
