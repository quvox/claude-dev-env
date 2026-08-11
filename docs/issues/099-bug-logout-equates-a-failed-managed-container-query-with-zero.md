---
id: 099-bug-logout-equates-a-failed-managed-container-query-with-zero
type: bug
origin_layer: 03
severity: 中
found: 2026-08-11
found_in: /task-close task-fix-logout-zero-target-path §6(独立レビュー Codex の指摘1 を裁定して起票)
related: docs/03-impl/relations/MODULE-cli-logout.md, docs/02-design/contracts/cli-container.md, docs/01-requirements/functional.md, claude-dev, claude-dev-mac
closes_when: 管理ラベル付きコンテナの列挙が失敗したとき「0件」と判定しなくなり、E2E-01 手順8 でそれを確認できたとき
summary: logout の手順4 が管理ラベル付きコンテナの docker ps の失敗を空集合へ変換するため、確認できていない状態で削除対象0件の経路に入りうる
---

# 099 管理ラベル付きコンテナの列挙の失敗が「0件」と同一視される

## 事象

`claude-dev logout` の手順4 は削除対象の Claude コンテナをこう引く(`claude-dev:963`〜`:968` /
`claude-dev-mac` の同一箇所):

```bash
    _targets=()
    while IFS= read -r _c; do
        [ -n "$_c" ] && _targets+=("$_c")
    done < <(docker ps -a --filter "label=claude-dev.managed=1" --format '{{.Names}}' 2>/dev/null || true)
```

`|| true` と `2>/dev/null` で**問い合わせの成否を捨てている**ため、`docker ps` が失敗しても
`_targets` は空になり、「管理ラベル付きコンテナは0件」と区別できない。
手順6 の0件判定は `[ ${#_targets[@]} -eq 0 ]` を見るので、この状態で共有ボリュームが空だと
**確認できていないのに**「削除対象がありません」を表示して終了コード 0 で終わる。

## 何が仕様に反するか

- `FR-env-03` 受入基準19 は0件の条件を「**管理ラベルを持つコンテナ(停止中を含む)が無く**」と
  定める。**「無いことを確認できた」ではなく「無い」という事実**を条件にしているので、
  引けなかった状態はこの条件を満たさない。
- `CTR-cli-container` のエラーケースは同じ倒し方を3箇所で明記している —
  「セッション由来の資源を引く問い合わせそのものが失敗した」/「遊休判定に使う Docker への
  問い合わせが失敗した」/ 2026-08-11 に新設した「`logout` が共有ボリュームが空かどうかを
  確かめられなかった」。**この3つと同型の経路が手順4 にだけ残っている。**
- `D0-scope-07` の観測点の定義「成功時と同じ表示・同じ終了コードになる」に当たる。

## 発生条件（狭い）

`docker ps --filter` が失敗し、かつ**同じ実行の中で `docker run`(共有ボリュームの検査)は成功する**
必要がある。daemon が落ちていれば両方失敗するので手順6 の印の条件で止まる。したがって
一過性のエラー・filter の構文エラー・部分的な権限エラーに限られる。**severity を「中」とした理由**は
この狭さと、共有ボリューム側の同型の欠陥(当時の `053`。`docs/histories/2026-08-11-fix-logout-zero-target-path.md` で解消)が「中」と裁定されていたことの一貫性である。

## 範囲外とした理由

`task-fix-logout-zero-target-path` の closure は手順6 の判定・手順4 のセッション由来の除外・
0件経路の表示であり、**手順4 の列挙の失敗の扱いは入っていない**。原則8 に従い直さずに起票する。
同型の全件列挙は行っていない(severity が「高」ではないため)。`_authfiles` は
ローカルの `[ -f ]` 判定なので問い合わせの失敗という状態を持たない。
