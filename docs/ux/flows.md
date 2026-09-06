---
id: ux-flows
updated: 2026-09-06
summary: 画面一覧(SCR-nn の台帳)と、ホスト CLI の主要な操作の流れ
---

<!-- docs/ux/flows.md: 冒頭の画面一覧が SCR-nn の台帳(唯一の定義場所)。
     現在の正だけを書く — 判断の理由は reviews/ へ。記述ルール: .claude/directions/ux.md -->

# 画面一覧と操作の流れ

## 画面一覧

| 画面ID | 画面名 | 目的 | 関連 UC |
|---|---|---|---|
| SCR-01 | cli-commands | コンテナ・認証・ポート・鍵の操作 | UC-01, UC-02, UC-03, UC-06 |

退役した画面の番号は再利用しない(退役の経緯は `reviews/00.md`)。

## 画面遷移

画面は1つなので、画面間の遷移を持たない。

```mermaid
stateDiagram-v2
  [*] --> SCR-01
  SCR-01 --> [*]
```

## 操作の流れ

いずれの流れも SCR-01(ホスト CLI)だけを通る。各流れの事前条件・事後条件は
`docs/01-requirements/usecases.md` の該当 UC が持つ。

### プロジェクトを隔離コンテナで開発開始(UC-01)

`claude-dev start` を打つ → 進捗行 → 完了時に接続 URL とアタッチを示す。
再実行では既存のコンテナへ再接続する。

### Web アプリをクライアントのブラウザで確認(UC-02)

`claude-dev forward` を打つ → 割り当てたポートと SSH トンネルを示す →
`claude-dev ports` で現在の割り当てを確認する。

### 危険な Docker 操作が拒否される(UC-03)

コンテナ内からの Docker 操作は中継の検査を経る。拒否されたときは原因と次の操作を示す。

### Codex CLI をコンテナで使う(UC-06)

`claude-dev login-codex` を打つ → デバイス認証の案内を示す → 以後は別プロジェクトの
コンテナでも再ログインなしで `codex` が使える。

### 資源を片付ける(`stop` / `logout` / `reset`)

不可逆な操作は、実行前に対象を示して確認を取る(`FR-env-03-14`)。
確認を経た後の各状態は `screens/SCR-01-cli-commands.md` の「状態」が持つ。
