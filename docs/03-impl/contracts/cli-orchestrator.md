---
id: cli-orchestrator
version: 1.1.0
updated: 2026-08-04
source:
  - docs/02-design/contracts/cli-orchestrator.md
kind: other
impl: claude-dev::main#orchestrate
summary: ホスト CLI(orchestrate)がオーケストレーターを起動・合流させるときの取り決め(実装側)
keywords: [契約, CTR, 実装]
verified:
  at: 2026-08-06
  version: 1.1.0
  against:
    - doc: docs/02-design/contracts/cli-orchestrator.md
      version: 1.1.0
---

# CTR-cli-orchestrator ホスト CLI(orchestrate) → orchestrator(実装)

- 実装: `claude-dev::main#orchestrate` / `claude-dev-mac::main#orchestrate`(発行側)、
  `orchestrator/main.go::main`(受け側)、`orchestrator/config.go::LoadConfig`(設定の解釈)
- 当事者: MOD-cli-orchestrate → MOD-orchestrator
- 対応する設計: `docs/02-design/contracts/cli-orchestrator.md`

## 実装上の事実

| 項目 | 実際の値 | 定義箇所 |
|---|---|---|
| 起動 | コンテナ内で `claude-orchestrator` を起動する。引数はゴール文字列(省略可)と `--fresh` | `claude-dev::main#orchestrate`, `orchestrator/main.go::main` |
| 生存判定 | `pgrep` 相当のプロセス存在で判定する(`tmux has-session` では判定しない) | `claude-dev::main#orchestrate` |
| セッション名の提示 | orchestrator が `--print-main-session` を持ち、CLI 側が名前を推測しなくて済む | `orchestrator/main.go::main` |
| コンテナ未起動(Linux) | `CLAUDE_DEV_NO_ATTACH=1` を付けて `start` を再帰的に呼んでから続行する | `claude-dev::main#orchestrate` |
| コンテナ未起動(macOS) | 先に `claude-dev start` を実行するよう表示して `exit 1` | `claude-dev-mac::main#orchestrate` |
| 空き殻セッション(Linux) | `kill-session` してから新規起動する | `claude-dev::main#orchestrate` |
| 設定の読み込み | **4段マージ(弱い順)**: ① 組込既定(`DefaultConfig`)→ ② `~/.config/claude-dev.yaml` の `orchestrator:` セクション → ③ `<workspace>/.orchestrator/config.yaml`(セクション無しのフラット)→ ④ 環境変数。**④ は Slack の資格情報だけに効く**(`SLACK_BOT_TOKEN` は常に環境の値で上書きし、`SLACK_CHANNEL` は空でないときだけ上書きする)。**段の落ち方は2段階**: ②③ のファイルが無い・開けない・走査に失敗したときは**その段を丸ごと適用しない**。ファイルは読めたが個々の値が型として不正なとき(`max_workers` に非数値や 0 以下 など)は**そのキーだけを適用せず、同じファイル内の正常なキーは適用する**(`applyConfigKV` がキー単位で検証する)。いずれの場合も起動は止めない | `orchestrator/config.go::LoadConfig`(`:67`〜`:90`), `orchestrator/config.go::DefaultConfig`, `orchestrator/config.go::applyConfigKV` |
| 設定ファイルの文法 | **YAML パーサを使わない自前の1行解析**。最初の `:` で分割し、**行末コメントの除去と前後の引用符の除去は行う**。空行・`#` 始まり・`:` を含まない行は飛ばす。**入れ子(2段以上)・複数行の値・アンカーは解釈しない**。ユーザー設定は `orchestrator:` セクションの**インデントされた行だけ**、プロジェクト設定は**インデントを無視した平坦な読み取り** | `orchestrator/config.go::parseFlatYAML`, `parseFlatYAMLSection` |
| モデル・effort | **設定では変えられない**。ポリシー表から決める | `orchestrator/models.go`(`MODULE-orchestrator-claude-exec`) |
| 再開/新規の判定 | plan の完了状況で判定する(専用のフラグやマーカーを持たない) | `orchestrator/state.go`, `orchestrator/plan.go` |

### 設定キーの実値(型・既定値・受理条件・不正値の扱い)

`applyConfigKV` は**キーごとに検証**し、条件を満たさない値は**そのキーだけを適用しない**。
警告もログも出さないため、**利用者は設定が効いていないことに気づけない**。適用しないとき
**組込既定へ戻るのではなく、より弱い段までのマージ結果がそのまま残る**。

| キー | 型 | 既定値 | 適用する条件 | 満たさないときの結果 | 定義箇所 |
|---|---|---|---|---|---|
| `max_workers` | 整数 | `5` | 整数として解析でき、かつ `> 0` | そのキーを適用しない | `config.go:97`〜`:100` |
| `stuck_limit` | 整数 | `3` | 同上 | 同上 | `config.go:101`〜`:104` |
| `max_review_rounds` | 整数 | `10` | 同上 | 同上 | `config.go:105`〜`:108` |
| `review_format_error_limit` | 整数 | `2` | 同上 | 同上。**利用時に `<= 0` なら 2 として扱う保険がある** | `config.go:109`〜`:112`, `review.go::Reviewer.RunGate` |
| `worker_grace_seconds` | 整数 | `10` | 整数として解析でき、かつ **`>= 0`**(0 は「猶予なし」の有効値) | そのキーを適用しない | `config.go:113`〜`:116` |
| `worker_model` | 文字列 | `sonnet` | 非空 | そのキーを適用しない。**適用されても選択には使われない**(DEPRECATED。解析のみ) | `config.go:117`〜`:120`, `models.go` |
| `reviewer_vendor` | 文字列 | `claude` | 非空 | そのキーを適用しない。**適用されても製品コードから一度も参照されない**(レビュアは常に Claude) | `config.go:121`〜`:124`, `docs/issues/012-modify-reviewer-vendor-setting-has-no-effect.md` |
| `merge_strategy` | 文字列 | `merge` | 非空(**列挙の検証をしない**) | そのキーを適用しない。**未知の値を設定できてしまい、統合時に `rebase` 以外はすべて `merge` として実行される** | `config.go:125`〜`:128`, `worker.go::ExecGit.Merge` |
| `worker_permission_mode` | 文字列 | `bypassPermissions` | **無条件**(空文字も適用する) | — 。空文字は「フラグを渡さない」を意味する有効値 | `config.go:129`〜`:130`, `worker.go::ExecClaude.RunPrompt` |
| `SLACK_BOT_TOKEN`(環境変数) | 文字列 | 空 | 常に環境の値を採る | 空なら通知を行わない(no-op) | `config.go:85`, `slack.go::SlackNotifier.Notify` |
| `SLACK_CHANNEL`(環境変数) | 文字列 | `U5SJG0XEK` | 非空のときだけ上書き | 空なら既定を保つ | `config.go:86`〜`:88`, `config.go::DefaultSlackChannel` |

**未知のキーは黙って無視する**(`applyConfigKV` の `switch` に該当しないものは何もしない)。

### 字句解釈の実際(`splitKV` / `parseFlatYAML` / `parseFlatYAMLSection`)

`splitKV`(`config.go:197`〜`:219`)の実測結果:

| 入力 | キー | 値 |
|---|---|---|
| `max_workers: 5` | `max_workers` | `5` |
| `max_workers:5`(空白なし) | `max_workers` | `5` |
| `max_workers: 5 # 並行度` | `max_workers` | `5`(**行末コメントを落とす**) |
| `merge_strategy: "rebase"` | `merge_strategy` | `rebase`(**前後の引用符を落とす**) |
| `worker_permission_mode: ''` | `worker_permission_mode` | 空文字(**フラグを渡さない指定として機能する**) |
| `  max_workers: 8`(インデント) | `max_workers` | `8`(**インデントは落とす**) |
| `orchestrator:` | `orchestrator` | 空文字(既知のキーに一致しないので無害に無視される) |
| `slack: url: http://x#y` | `slack` | `url: http://x#y`(**2つ目以降の `:` は値の一部**。引用符が無くても ` #` が無いのでコメント除去は起きない) |
| `- 1` | — | **`:` を含まないので無視** |

読み取りの違い:

- `parseFlatYAML`(プロジェクト設定)は**全行に `splitKV` を適用する**。インデントを落とすため、
  `orchestrator:` 配下に書いても**同じ結果になる**(セクションの概念を持たない)。
- `parseFlatYAMLSection`(ユーザー設定)は**インデントされた行だけ**を対象にし、インデントの無い行で
  セクションの内外を切り替える。したがって**セクション無しで平坦に書くと1件も適用されない**。
- **重複キーは後の行が勝つ**(map への代入)。

**解析できなかった行は警告もログも出さずに捨てる**(終了コードも変わらない)。

## 設計との差異

| 項目 | 設計(02) | 実装(03) | どちらが正か |
|---|---|---|---|
| 実行中の run への再接続(macOS) | 生存判定で合流する | **macOS 版は生存判定を持たず**、新しいウィンドウでコントローラがもう1つ起動しうる。`claude-dev attach` で入り直す運用で回避している | **実装が現状**。設計の期待(OS によらず同じ観測可能な結果。`FR-env-10` 受け入れ基準4)を満たしていないため、`docs/issues/003-future-macos-orchestrator-scope.md` で追跡する |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| macOS でコントローラの生存判定が無い | 二重起動が起きうる | `docs/issues/003-future-macos-orchestrator-scope.md` |
| 不正な設定値を**黙って無視**する(警告もログも出さない) | 設定したつもりの値が効かないまま実行が進む。しかも「既定値に戻る」ではなく「より弱い段の値が残る」ため、利用者の予想と二重にずれうる | なし(起票の閾値の外: **`FR-orch-03` 受入基準8 がこの振る舞いを要件として定めている**。個別に被害が特定できるキーは `docs/issues/012` / `022` が追跡) |
| `merge_strategy` の列挙を検証しない | `rebase` 以外の綴り間違い(例: `rebse`)が `merge` として通り、利用者は rebase したつもりでマージされる | `docs/issues/022-modify-merge-strategy-enum-is-not-validated.md` |
| `reviewer_vendor` が製品コードから参照されない | 設定しても常に Claude がレビューする | `docs/issues/012-modify-reviewer-vendor-setting-has-no-effect.md` |
| 解析できなかった行を黙って捨てる | ユーザー設定を**セクション無しで平坦に**書くと1件も適用されず、警告も出ない(プロジェクト設定は逆にインデントを許す)。**この非対称は利用者に伝わらない** | なし(閾値の外: **`CTR-cli-orchestrator` の「設定ファイルの字句規則」が契約として明文化された**。個別キーが効かない事象は `docs/issues/012` / `022` が追跡) |
