# task-stop-session-spawned-containers — 解決済みの経緯 1

> フェーズ1(`/task-new`)で人間が回答した決定シートの写し。
> フェーズ2(`/task-doc`)が `new-features/00-requests/decisions/env.md` と
> `new-features/01-requirements/decisions/split.md` へ反映し終えたので、
> `.claude/directions/task-memo.md` §2 に従ってここへ追い出した。
> **実体の入力フォームは `sheet.md`**(論点4 が回答待ちで生きている)。

## 決定シート(回答済み)

| # | 論点 | 回答 | 反映先 |
|---|---|---|---|
| 概念1 | 「セッションのコンテナ内から起動された Docker コンテナ」の外延 | **推奨どおり**(記入は「含む」)。含む = compose 経由 + `docker run` / `docker create`(`created` 状態を含む)。含まない = 別セッション由来 / ホストで直接作ったもの / VM モードのゲスト内 / 本変更より前に作られたもの | `D0-env-05` 項2 / `docs/00-requests/decisions/env.md` |
| 概念2 | 「終了する」の外延 | **推奨どおり**(記入は「削除」)。`docker rm -f` で削除する。名前付きボリュームとイメージは削除しない | `D0-env-05` 項2 / `FR-env-01` の新条項 |
| 概念3 | 片付ける資源の種類 | **推奨と異なる**(記入は「コンテナとネットワーク。」)。**セッション内から作られたネットワークも削除対象に含める**(AI推奨は「コンテナ + compose 既定ネットワークまで」だった)。名前付きボリュームは対象外のまま。**理由(人間)**: 「片付けの範囲を『セッションが作ったものは全部』としたい」 — 資源ごとの害の大小ではなく、範囲を1文で言い切れることを優先する(気づきは `docs/feedbacks/024-cleanup-scope-is-defined-by-ownership-not-by-harm.md`) | `D0-env-05` 項2 / `FR-env-01` の新条項 / `CTR-docker-api`(`POST /networks/create` への注入) |
| 概念4 | この片付けを行うコマンド | **推奨どおり**(記入は「stopとreset」)。`stop` と `reset` に入れ、`logout` には入れない | `D0-env-08` / `MODULE-cli-stop` / `MODULE-cli-reset` |
| 概念5 | 所有者の印は誰が付けるか | **推奨どおり**(記入は「つけて良い」)。docker-proxy が所有者ラベルを付与してよい | `D0-env-08` 項7 / `D0-env-10` / `CTR-cli-container` / `CTR-docker-api` |
| 概念6 | 印を付けられなかったコンテナ | **推奨どおり**(記入は「推奨で良い」)。片付けの対象外とし表示もしない。事実は 03 の「既知の制限」に書く | `MODULE-cli-stop` / `MODULE-docker-proxy-serve` の「既知の制限」 |
| 論点1 | 「このセッションが作った」の実現方式 | **A**(docker-proxy が作成要求へ所有者ラベルを注入する) | `D0-env-08`(新項)/ `CTR-docker-api` |
| 論点2 | 所有者ラベルの値 | **A**(起動ディレクトリの絶対パス。`claude-dev.project-dir` と同じ値) | `CTR-cli-container`「管理ラベル」 |
| 論点3 | `stop` に確認(y/N)を求めるか | **A**(求めない。`D0-env-08` 項3 の裁定を維持し、判定基準の文言だけを直す) | `D0-env-08` 項3 |
| 委任1 | 所有者ラベルの名前・値の形式・注入の実装細部 | **承認**(ガードレール5件つき。**注入する API 経路も委任範囲**なので、概念3 で必要になった `POST /networks/create` への注入もここで決める) | `D0-env-10`(委任範囲の拡張) |
| 方針合意 | 各ドキュメントへの変更方針 | **異議なし(空欄)** | - |
