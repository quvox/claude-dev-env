---
id: 2026-08-19-doc-check-ssot-stop-cleanup-and-project-env-recertification
date: 2026-08-19
task: task-stop-cleanup-and-project-env(フェーズ4 の `/doc-check ssot`。タスクは未完了のまま)
origin_layer: 03
issue: docs/issues/103, docs/issues/104(いずれも本記録で新規に起票)
summary: 反映直後の SSOT 20 本を検証して合格証を発行し、実装欠陥2件を起票し、実装で腐ったコード引用 28 箇所ほかを直した
---

# 2026-08-19 `/doc-check ssot task-stop-cleanup-and-project-env`

## 変更理由

`task-stop-cleanup-and-project-env` の変更指示 26 本が SSOT へ反映され(`compose-applied.json`)、
closure の 20 文書が合格証を失った。`close-task.py` 条件 (b) はこの合格証を要求するので、
反映直後の SSOT を検証して発行し直す必要があった。

独立レビューは **Codex(`gpt-5.6-sol` / reasoning high)**。読み取り専用のサブエージェント3本に
00/01・02・03 の照合(反映の逐語一致、コード引用の実在、カバレッジ)を委ねた。

## 変更内容の要約

- **`docs/issues/103` を起票した(重大度 中)。** `reset)` 分岐が `--volumes` を解析しておらず
  (`claude-dev:2281`-`:2283` / `claude-dev-mac:2323`-`:2325`)、解析ブロックは直前の `logout)`
  分岐に置かれている。`case` は1分岐しか走らないので `claude-dev reset --volumes` は
  **セッション由来の名前付きボリュームを1件も削除しない**。`FR-env-01-32` が未実装である。
  `MODULE-cli-reset` の手順1・引数表・「既知の制限」に事実を書いて 03 を実装の鏡へ戻した。
- **`docs/issues/104` を起票した(重大度 中)。** `.gitignore` への追記(`claude-dev:1555` /
  `claude-dev-mac:1630`)が `set -e` の下の単純コマンドなので、書き込めない `.gitignore` では
  `start` がそこで終了し、`FR-env-14-4` が課す「外せなかったことを表示して起動を続ける」に
  入らない。`MODULE-cli-start` 手順5-2 の 8 と「既知の制限」へ事実を書いた。
- **`FR-env-01-25` が `FR-env-01-33` と正面から矛盾していた**(用語「セッション由来の資源」に
  ボリュームが入ったのに、`reset` の無条件削除の条項に但し書きが降りていなかった)。
  `FR-env-01-22` と同型の但し書きを足した。
- **コード引用 28 箇所を実コードで取り直した。** フェーズ3 の実装で `claude-dev` /
  `claude-dev-mac` が +147 行ほど伸び、実装前に書いた `path:line` がすべてずれていた。
- **`--volumes` が 02 の CLI 画面(`SCR-01`)のフラグ欄に無かった。** 条項の充足を `完全` と
  書きながら利用者から見えるフラグが設計に無い状態だったので足した。
- **予約する環境変数名の照合規則(大文字小文字を区別する完全一致 / 接頭辞は前方一致)が
  02 に無く、03 が `[DS-04]` で発明していた。** `FR-env-14-8` が「02 の契約が定める」と指名して
  いるので 02 へ書いた。
- `PLAN-cli-common-write-project-ssh-keys` / `PLAN-cli-ssh-keys-reset` の契約列が `なし` のまま
  03 だけ `CTR-cli-container` になっていた(02⇄03 の片側更新)ので 02 を揃えた。
- `03-impl/index.md` の「実装の欠陥として起票済み」が **4件と言いながら 002 を含む5件を列挙**
  していた。002 を外し、新設の `103` を加えて **5件** にした。
- `tests/cli-stop.md` と `tests/cli-start.md` で連番が二重化していたので通し番号へ直した。
- `tests/docker-proxy.md` の「機能間連携仕様書 ⇄ テスト」行にボリューム経路のテスト4本が
  落ちていたので足し、テスト本数 39/39 を **45/45** に直した。
- **コードは1バイトも変更していない。**

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/00-requests/decisions/env.md | 1.6.1 → **1.7.0** | `D0-env-05` 項2 に残っていた動詞「停止」を `D0-env-08` 項2 の改訂へ揃えた |
| docs/00-requests/acceptances.md | 1.6.0 → **1.6.1** | `summary` の AC 列挙を実体(AC-01〜03 / 06〜08)へ |
| docs/00-requests/request.md | 1.6.0(据え置き) | 合格証の発行のみ |
| docs/00-requests/terminology.md | 1.7.0(据え置き) | 同上 |
| docs/00-requests/decisions/sec.md | 1.4.0(据え置き) | 同上 |
| docs/01-requirements/functional.md | 1.18.0 → **1.19.0** | `FR-env-01-25` の但し書き / `-26` の種別へボリューム / `FR-env-14-3` へ常駐プロセスのログ / `FR-env-07` の参照範囲 22〜27 → 22〜31 / `summary` の FR 範囲 |
| docs/01-requirements/usecases.md | 1.7.0(据え置き) | 合格証の発行のみ |
| docs/01-requirements/decisions/split.md | 1.5.0(据え置き) | 同上 |
| docs/02-design/architecture.md | 1.7.0(据え置き) | 同上 |
| docs/02-design/system.md | 2.14.0 → **2.15.0** | `SCR-01` のフラグ欄へ `--volumes` |
| docs/02-design/relations.md | 1.11.0 → **1.11.1** | 2つの `PLAN-*` の契約列へ `CTR-cli-container` / `PLAN-cli-start` の設計判断へ `DSN-env-05` |
| docs/02-design/logging.md | 1.9.0(据え置き) | 合格証の発行のみ |
| docs/02-design/contracts/cli-container.md | 1.12.0 → **1.13.0** | 予約名の照合規則 / 「上の規則 D」→「下の…」 |
| docs/02-design/contracts/docker-api.md | 1.2.0(据え置き) | 合格証の発行のみ |
| docs/03-impl/index.md | 1.26.0 → **1.27.0** | 起票済み欠陥 4件(内訳5件)→ **6件**(`103` / `104` を加え `002` を外した)/ `help` 分岐の行番号 |
| docs/03-impl/tests/cli-stop.md | 1.8.0 → **1.8.1** | 連番の二重化(9〜13 の重複)を 17〜21 へ |
| docs/03-impl/tests/cli-start.md | 1.5.0 → **1.5.1** | 連番の重複(33 が2行)を通し番号へ |
| docs/03-impl/tests/docker-proxy.md | 1.4.0 → **1.4.1** | MODULE 行へボリューム経路のテスト4本 / 39件 → 45件 |
| docs/03-impl/tests/cli-reset.md | 1.5.0(据え置き) | 合格証の発行のみ |
| docs/03-impl/tests/e2e.md | 1.11.0(据え置き) | 同上 |
| docs/03-impl/relations/MODULE-cli-reset.md | (版を持たない) | `--volumes` を受理していない事実を手順1・引数表・既知の制限へ / コード引用8箇所 |
| docs/03-impl/relations/MODULE-cli-stop.md | (版を持たない) | コード引用6箇所 |
| docs/03-impl/relations/MODULE-cli-start.md | (版を持たない) | `load_project_env_file` の実行位置(手順12 のブロック内)/ `.gitignore` 追記失敗で起動が止まること(`docs/issues/104`)/ コード引用9箇所 |
| docs/03-impl/relations/MODULE-cli-common-spawned-resources.md | (版を持たない) | コード引用5箇所 |
| docs/03-impl/relations/MODULE-cli-common-write-project-ssh-keys.md | (版を持たない) | 案内コメント2行 → 3行 / 空行が節と一緒に落ちること |
| docs/03-impl/relations/MODULE-cli-ssh-keys-reset.md | (版を持たない) | 空行の扱い |

## 実装したもの

| 対象 | 内容 | コミット |
|---|---|---|
| なし | `/doc-check` はコードを変更しない | - |

## 実施した移行

なし

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 変更 | MODULE-cli-reset / -stop / -start / -common-spawned-resources / -common-write-project-ssh-keys / -ssh-keys-reset | 本文のコード引用と事実の訂正(`callers` / `callees` / `contracts` は変更なし) |
| 変化なし | 他55本 | 61本のまま(`check-relations.py` 合格) |

## 検討した代替案

| 論点 | 採用した案 | 棄却した代替案 | 棄却の理由 / 崩れる条件 |
|---|---|---|---|
| `reset --volumes` 未実装をどう扱うか | **03 に事実(受理していない)を書いて `既知の制限` と issue で追跡し、01・02 の要件は動かさない** | 03 から `--volumes` の記述ごと削る | 削ると「何を作るはずだったか」が消え、`/task-close` が欠けた機能ごと閉じる。**崩れる条件**: 人間が `FR-env-01-32` そのものを取り下げると決めたとき |
| 予約名の照合規則の置き場 | **02 の契約へ書く** | 03 の `[DS-04]` のままにする | `FR-env-14-8` が「どの名前が本システムのものかは 02 の契約が定める」と 02 を唯一の正に指名している。**崩れる条件**: 01 がその指名をやめたとき |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 新規 issue | docs/issues/103 | `reset` が `--volumes` を解析しない(重大度 中 / 起点層 03) |
| 新規 issue | docs/issues/104 | `.gitignore` へ書き込めないと `start` が止まる(重大度 中 / 起点層 03) |
| 残務(3行) | docs/pendings.md | `FR-env-07-11`・`-12` が UC に無い / `system.md` の主担当が複数モジュールの行 / `--volumes` が組み込みヘルプに出ない |
| 鮮度の報告 | 本記録 | `P-005`・`P-006` の解消条件は未発火。`docs/issues/002` と `092` は本タスクの実装で解消済み(削除は `/task-close` の裁定) |
| 知見 | 今回限り(理由: 検証手順そのものの気づきであり、製品の決定にはならない) | **実装より前に書いた `path:line` は、その実装が入った瞬間に全部腐る。** フェーズ4 の `/doc-check` は引用の取り直しを前提に組むこと |

## 残務の恒久受容(2026-08-19 実行)
この一覧は `doc-health.py --as-of --sweep` が落とした行である。落としたこと自体が決定であって、指摘でも新しい issue でもない(`.claude/directions/issues-pendings.md` §2.1)。
- - 2026-08-10 `docs/03-impl/tests/*.md`:状態列が「対象外(理由: …)」を使っているが、2026-08-10 のキット書き換え後の `build-index.py` は「テスト対象外」だけを数えるため、`tests/index.md` の第3列が全て 0 になる差分が出る(本タスクの範囲外なので `git checkout` で戻した)。語彙をどちらへ揃えるか決めて一括で直す。
  - 理由: 対象が実在しない: docs/03-impl/tests/*.md`

## 追記(同日。`/task-close` の中で)

**本記録が起票した `docs/issues/103` と `104` は、同じタスクの中でコードを直して解消したので削除した**
(`.claude/directions/issues-pendings.md` §1 の行1「現タスクの範囲で直すべきか → 直す。新しい記録は作らない」)。
この検証を走らせた `/doc-check` はコードを書けないので起票が正しい扱いだったが、
呼び出し元の `/task-close` はコードへ戻せるため、記録として残すのではなく直した。

| 起票していた issue | 直した内容 | 確認 |
|---|---|---|
| `103` `reset` が `--volumes` を解析しない | `--yes` のみを解析する同一のブロックが `logout)` にもあり、フェーズ3 の置換が先に現れた `logout)` に当たっていた。`logout)` を元の形へ戻し、`reset)` に新しい解析を置いた(`claude-dev:2274`-`:2287` / `claude-dev-mac:2316`-`:2329`) | `claude-dev reset --volumes` を**非対話・`--yes` 無し**で実行し、削除対象の列挙に「セッション由来のボリューム: cdx-reset-probe」が現れ、そのうえで何も削除せず中止することを実機で確認した。`--volumes` 無しでは列挙に現れないことも確認した |
| `104` `.gitignore` へ書き込めないと `start` が止まる | 追記を `if ! echo … >> …; then` の形にし、失敗しても表示して続けるようにした(`FR-env-14-4` / `NFR-avail-03`) | `bash -n` と `go test ./...`。読み取り専用の `.gitignore` を作る実機確認はフェーズ4 では行っていない(次に `start` を触るタスクの実機確認で拾う) |

あわせて **`--volumes` を組み込みヘルプへ足した**(この記録が残務として挙げていたもの)。
`docs/03-impl/relations/MODULE-cli-reset.md` と `MODULE-cli-start.md` の該当記述、
および `docs/03-impl/index.md` の件数(6件 → **4件**)を実物へ戻した。
**残務3行を落とした**: `--volumes` のヘルプ(直した)/ 既に追跡下の env ファイルを検出できない
(**実装が `git check-ignore -q` で検出して手順を表示する**ので事実でなくなった)/
実装前の `tests:` が未実在のテストを挙げる(**実装してテストが実在するようになった**)。
