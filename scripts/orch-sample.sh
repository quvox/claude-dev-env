#!/usr/bin/env bash
#
# orch-sample.sh — オーケストレーター自己検証用サンプルの scaffold。
#
# examples/orch-sample/ テンプレート（正本）を workspace/orch-sample/ の使い捨て
# 作業コピーへ展開し、独立 git リポジトリとして初期化する。冪等（--force で
# 既存をクリーン初期化）。正本仕様は docs/impl/70_sample-project.md。
#
# 使い方:
#   scripts/orch-sample.sh [--force] [--seed]
#     --force  出力先が既存なら削除して作り直す（未指定で既存ならエラー）
#     --seed   seed/plan.json を作業コピーの .orchestrator/plan.json に配置する
#
set -euo pipefail

# リポジトリルートをスクリプト位置から解決（scripts/ の親）。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

TEMPLATE_DIR="${REPO_ROOT}/examples/orch-sample"
DEST_DIR="${REPO_ROOT}/workspace/orch-sample"

FORCE=0
SEED=0
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    --seed)  SEED=1 ;;
    *)
      echo "orch-sample.sh: 不明な引数: $arg" >&2
      echo "使い方: scripts/orch-sample.sh [--force] [--seed]" >&2
      exit 2
      ;;
  esac
done

if [ ! -d "$TEMPLATE_DIR" ]; then
  echo "orch-sample.sh: テンプレートが見つかりません: $TEMPLATE_DIR" >&2
  exit 1
fi

# 1. 出力先の扱い。既存かつ --force なら削除、既存かつ未指定ならエラー。
if [ -e "$DEST_DIR" ]; then
  if [ "$FORCE" -eq 1 ]; then
    echo "orch-sample.sh: 既存の $DEST_DIR を削除します (--force)"
    rm -rf "$DEST_DIR"
  else
    echo "orch-sample.sh: $DEST_DIR は既に存在します。--force で再生成してください。" >&2
    exit 1
  fi
fi

# 2. テンプレート本体をコピー（seed/ は除く）。
mkdir -p "$DEST_DIR"
# ドットファイルも含めコピーし、seed/ ディレクトリだけ除外する。
( cd "$TEMPLATE_DIR" && \
  find . -mindepth 1 -maxdepth 1 ! -name 'seed' -exec cp -R {} "$DEST_DIR/" \; )

# 5. 作業コピー直下の .gitignore に運用状態 .orchestrator/ を追記（無ければ作成）。
#    テンプレート同梱の .gitignore（Python キャッシュ除外）を保持しつつ追記する。
if ! { [ -f "$DEST_DIR/.gitignore" ] && grep -qxF '/.orchestrator/' "$DEST_DIR/.gitignore"; }; then
  printf '/.orchestrator/\n' >> "$DEST_DIR/.gitignore"
fi

# 3. コピー先で git init ＋ 全ファイルを初期コミット。
#    user.name/email が未設定の環境でも動くよう -c で明示する。
GIT_ID=( -c user.name=orch-sample -c user.email=orch-sample@example.invalid )
git -C "$DEST_DIR" init -q
git -C "$DEST_DIR" "${GIT_ID[@]}" add -A
git -C "$DEST_DIR" "${GIT_ID[@]}" commit -q -m "chore: scaffold orch-sample working copy"

# 4. --seed 指定時のみ seed plan を .orchestrator/plan.json に配置。
#    .gitignore 済みなので初期コミットには含まれない（運用状態は追跡しない）。
if [ "$SEED" -eq 1 ]; then
  mkdir -p "$DEST_DIR/.orchestrator"
  cp "$TEMPLATE_DIR/seed/plan.json" "$DEST_DIR/.orchestrator/plan.json"
  echo "orch-sample.sh: seed plan を配置しました: $DEST_DIR/.orchestrator/plan.json"
fi

echo "orch-sample.sh: 完了 -> $DEST_DIR"
