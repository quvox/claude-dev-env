# task-relations-code-sync 解決済みの経緯 1

<!-- memo.md から追い出したもの。仕様ドキュメントではない(version / verified を持たない)。
     タスクの削除と一緒に消える(close-task.py)。 -->

## 着手時の再突き合わせ(タスク0。2026-08-05 に完了)

### 1本目の反映で消えた行(closure から外した)

| # | 対象 | 消えた理由(コードで確認) |
|---|---|---|
| `038` #6 | `MODULE-cli-pull` 異常系 | `MODULE-cli-pull.md:88` が `set -e` による非0終了を明記済み(`issue 037` の再裁定で解消) |
| `038` #7 | `MODULE-cli-reset` 異常系 | **コードが変わった**。`claude-dev:2007`〜`:2011` は非 TTY かつ `--yes` 無しで `exit 1`。doc も `exit 1` を書いている(ただし言い回しに残留 → 論点6) |
| `038` #8 | `MODULE-cli-start` 処理の流れ・副作用 | Linux / macOS の差が本文に入った(`MODULE-cli-start.md:130`〜`:133` の `CLAUDE_DEV_NO_ATTACH` と判断11 の `require_setup` 実行順) |
| `038` #24 | `MODULE-cli-stop` 実装上の判断 | `MODULE-cli-stop.md:154`,`:195`,`:196` が「握らないのは本体と docker-proxy の2つだけ」と書き、`claude-dev:1667` に `\|\| true` が無いことと一致。自己矛盾も解消 |
| `038` #25 | `MODULE-cli-logout` 処理の流れ | 全面書き替え済み。列挙は管理ラベルで行うと書き、`container_exists` を Claude コンテナに使うという記述は消えている |
| `038` #26 の `stop` 分 | `MODULE-cli-stop` の行番号根拠 | 行番号の引用そのものが無くなった(`grep` で 0 件) |
| `038` #32 | macOS の `xargs -r` | **コードが変わった**。`claude-dev:1651` / `claude-dev-mac:1609` は明示ループへ置き換わり、両 OS の `xargs` 依存が消えた |
| `038` 追加#7 | `MODULE-orchestrator-review` 既知の制限 | `:122` が `issue 034` を「裁定済み・不一致は解消」と書いている |
| `038` 追加#8 / `028` 追加分 | `03-impl/index.md` / `03-impl/contracts/cli-container.md` | 件数の明記と「設計との差異」の訂正が済んでいる(`index.md:60` / `cli-container.md:71`) |

## 着手時の再突き合わせ(タスク0。2026-08-05 に完了)— 前提の確認と残件の内訳

**方法**: (1) `git log` で 1本目の反映後に動いたファイルを特定 → (2) 動いたファイルの該当節を読み、
コード(`claude-dev` / `claude-dev-mac` / `scripts/entrypoint-claude.sh` / `orchestrator/*.go`)と
1行ずつ突き合わせ → (3) 動いていないファイルは**コードも動いていないこと**を確認して残件と判定。

**前提の確認**: `orchestrator/` の最終変更は **2026-07-06**(`b634206`)で、
`03-impl/relations/MODULE-orchestrator-*.md` の最終変更は **2026-08-04**(`461f25c` = `task-impl-depth`
の反映、および `a97e9d5`)である。**issue が書かれた後にコードもドキュメントも動いていない**ので、
orchestrator の行は全件がそのまま残件である(下の3件を抜き取って裏取りした)。

| 対象 | 抜き取り確認 | 結果 |
|---|---|---|
| `038` #16 | `orchestrator/term.go:34`,`:44`,`:48`,`:96` ⇄ `MODULE-orchestrator-term.md:48`,`:61` | **残件**(doc は `options` = 文字列の並び / 3関数が `error` を返すと書く。実体は `items []menuItem` / `(func(), bool)` / 戻り値なし / `bool`) |
| `032` #6 | `orchestrator/*.go`(非テスト)への `LastSummary` / `AssumptionsN` / `InterventionsN` の代入 | **残件**(代入は0件。`dashtui.go:233`,`:239` が表示だけしている) |
| `038` #22 | `orchestrator/mode.go:191` の `ResolveArgsOne` の呼び出し元 | **残件**(定義とコメントだけ。製品コードからの呼び出しは0件) |

### 1本目の反映で消えた行(closure から外した)

**memo-1.md に移動**(1本目 `task-fix-destructive-scope` の反映で解消した9行の内訳。closure から外した根拠。フェーズ2 以降で参照する必要は無い)。

### 残件と確認した cli 行(closure に残した)

| # | 対象 | 現物 |
|---|---|---|
| `038` #9 | `MODULE-cli-start` の `### MODULE-entrypoint-claude` 節と `永続化` 欄 | `/workspace/.codex/config.toml` の補完・`/workspace/CLAUDE.md` の自動更新・VNC 時の `.mcp.json` / `.claude.json` 更新がどちらにも無い(実体は `scripts/entrypoint-claude.sh:263`,`:517`〜`:608`,`:614`〜`:672`。`MODULE-entrypoint-claude.md` 側には手順17・18 として書かれている) |
| `038` #26 の `start` 分 | `MODULE-cli-start.md:169` | `claude-dev:419` / `claude-dev-mac:486` を entrypoint 起動箇所として引くが、**現在その行はロックの警告出力**である。主コンテナの `docker run -d` は `claude-dev:1381` / `claude-dev-mac:1414`、docker-proxy は `claude-dev:710` / `claude-dev-mac:777` |

### 新たに closure へ入れた行

| 対象 | 理由 |
|---|---|
| `MODULE-docker-proxy-serve` の既知の制限 | `docs/issues/005` の対処案1 が「**`issue 038` の relations 全面揃えと同じタスクで行う**(同じ層の同じ性質の修正を分割しないため)」と指定している。`:111`〜`:117` の表に該当行が無いことを確認した |

## 前タスクからの申し送り(task-fix-destructive-scope フェーズ4 で転記。2026-08-04)

- **`task-fix-destructive-scope` は完了した。** SSOT が動いたので、**本タスクの変更指示を
  新しい SSOT に対して読み直すこと**(`/doc-check` が失効を検出する)。
  とくに次のファイルが動いた: `03-impl/contracts/cli-container.md`(1.3.0 → 1.4.0。
  実装上の事実を全面的に取り直し、7行追加)/ `03-impl/index.md`(1.8.0 → 1.9.0。
  本数 82 → 83、起票済み 16 → 15 件)/ `MODULE-cli-start` / `-stop` / `-reset` / `-logout`
  (戻り値・副作用 / 異常系 / 既知の制限 / 並行性 を全面的に書き替えた)/
  `03-impl/features.md`(`MODULE-cli-common-lock` を追加して 83 機能)。
- **`docs/issues/038` / `032` の relations 乖離**は本タスク(2本目)の担当のまま。
  ただし **`MODULE-cli-start` / `-stop` / `-logout` / `-reset` / `-login` / `-login-codex` の
  6本は 1本目が実装から書き直したので、乖離の件数を数え直すこと**(1本目が閉じた分がある)。
