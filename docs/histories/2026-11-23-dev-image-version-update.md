---
id: 2026-11-23-dev-image-version-update
date: 2026-11-23
record: docs/build-records/dev-image-version-update.md
critical: false
origin_layer: 03
issue: なし
summary: 開発イメージの Go・Python・Node・nvm・noVNC・terraform を公式配布情報で引いた最新の安定版へ上げ、CI の部品は最新メジャーであることを確かめた
---

# 2026-11-23 開発イメージと CI の部品の版更新

## 変更理由

### R-01 人間の更新指示

- 起点層・根拠: 人間の要望 2026-11-23「goやpythonおよび依存モジュールなど全てについて確認して、アップデートして」(`.claude/missions/2026-11-23-version-update/requests.md`)。版の選び方は `delegation.md` §2.3(最新の安定版、Node は最新 LTS)
- 変更が必要になった条件: 固定していた版(Go 1.26.1・CPython 3.11.11 / 3.13.14 / 3.14.7・nvm v0.40.6・noVNC v1.6.0・Node 既定 24 系)がいずれも最新でなくなった

### R-02 terraform の版の解決の不具合

- 起点層・根拠: R-01 の起動確認で、terraform が最新(1.17.2)ではなく v1.9.8 で入っていると判った。基準コミット c007dc2 の既存イメージも同じで、元からの不具合
- 変更が必要になった条件: `releases.hashicorp.com/terraform/index.json` の versions が版の順に並んでいないのに、並べ替えずに `last` を取っていた

## 変更内容の要約

- Go 1.27.4、CPython 3.11.18 / 3.13.18 / 3.14.10 / 3.15.2(global は 3.13.18)、Node の既定(fnm・nvm)を 26 系へ、fnm にも 22 / 24 / 26、nvm v0.41.0、noVNC v1.7.0
- Node 25 以降は corepack を同梱しないため、pnpm の導入の前に `npm install -g corepack@latest` を足し、`pnpm --version` で本体をイメージへ焼き込む
- terraform は正式版だけを数値で並べ替えて最大を取る
- 据え置き: 基底 `ubuntu:24.04`、CI の actions(全件が最新メジャー)、arm64 実行機 `ubuntu-24.04-arm`

## 更新した仕様ドキュメント

| 理由ID | 仕様ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|---|
| R-01 | docs/03-impl/environments/images.md | 1.5.0 → 1.6.0 | Python・Node・Go・nvm の既定値を新しい版へ。DS-04 の行(global の系列・同梱系列・Node 既定・基底の据え置き)を足し直し、corepack の落とし穴を足した。`source:` に architecture.md を足した(残務の解消) |

## 実装したもの

| 理由ID | 対象 | 内容 | コミット |
|---|---|---|---|
| R-01 | .devcontainer/Dockerfile.claude | 版の固定値の更新、fnm の既定を 26 系に、corepack の導入、pnpm の焼き込み | 08d074d |
| R-02 | .devcontainer/Dockerfile.claude | terraform の版の解決を並べ替えに直した | 08d074d |

## 実施した移行

なし

### ロールバック・復旧記録

| 理由ID | 不可逆点 | 切り戻し可能な条件・期限 | 切り戻し手順 / forward-fixのみの理由と復旧手順 | 復元元 | 確認日 | 復旧確認コマンド・結果 |
|---|---|---|---|---|---|---|
| R-01 | 適用外(critical: false。イメージは作り直せる) | — | — | — | — | — |

## 機能間連携仕様書の変化

なし(イメージのビルド定義は relations の外)

## 検討した代替案

| 論点 | 採用した案 | 棄却した代替案 | 棄却の理由 / 崩れる条件 |
|---|---|---|---|
| Python 3.11 系 | 最新パッチへ上げて残す | 外す | まだサポート中(2027-10 まで)で、最初の要望が名指した系列 / 崩れる条件: EOL を迎えたとき |
| Python 3.15 系 | 足す | 足さない | 最新の安定系列が入っていない状態は更新にならない / 崩れる条件: ビルド時間が問題になったとき |
| `pyenv global` | 3.13 系の最新パッチ | 3.15 系へ上げる | 既定の系列の変更は指示されておらず、利用者のスクリプトが黙って壊れうる / 崩れる条件: 上げる指示が出たとき |
| Node の既定 | 最新 LTS の 26 系 | 24 系のまま | §2.3 は最新 LTS を選ぶと定める / 崩れる条件: 同梱 CLI が 26 系で動かないとき |
| 基底 OS | ubuntu:24.04 のまま | ubuntu:26.04 | 26.04 は coreutils と sudo が別実装に置き換わっており、版の更新ではなく振る舞いが変わる種類の変更 / 崩れる条件: 基底の更新が指示されたとき、24.04 の標準サポート終了(2029-04)が近づいたとき |
| pnpm の入れ方 | npm から corepack を入れて従来の手順を保つ | `npm install -g pnpm` | 既存の導入手順(corepack の shim)を変えずに済む / 崩れる条件: corepack をやめると決めたとき |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 知見 | 今回限り(イメージ固有の事実で、images.md の落とし穴に既に書いた) | Node 25 以降の公式配布は corepack を同梱しない。Node の既定を上げるときは corepack に頼る導入を見直す |
| 解消した残務 | docs/residual.md(2026-09-01 の images.md `source:` の行) | `source:` に `docs/02-design/architecture.md` を足して直した |

## 残務から落とした行(解消)
- 2026-09-01 docs/03-impl/environments/images.md:frontmatter `source:` が `docs/02-design/environments.md` だけを挙げているが、同ファイルはサービスとポートの表しか持たず、イメージのステージ構成の設計意図は `docs/02-design/architecture.md` の `DSN-dist-01` に在る(本文もその ID を引いている)。上流が動いたときにこの文書が失効することを機械が言えない。基準コミット 69579da より前から在る取りこぼしである(F3 実装整合フロー)
  - 判定: 直した
