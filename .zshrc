alias ls="ls -aF"
alias ll="ls -alF"
alias activate="source venv/bin/activate"
alias start-env="python3 -mvenv venv"
alias hibernate="sudo systemctl hibernate"

export PATH="$HOME/.local/bin:$PATH"

# pyenv (Python バージョン管理)
# システムの /etc/zsh/zshrc が先に初期化済みなら（shims が PATH にあれば）二重初期化を避ける。
export PYENV_ROOT="$HOME/.pyenv"
if [[ ":$PATH:" != *":$PYENV_ROOT/shims:"* ]]; then
  [ -d "$PYENV_ROOT/bin" ] && export PATH="$PYENV_ROOT/bin:$PATH"
  command -v pyenv >/dev/null 2>&1 && eval "$(pyenv init - zsh 2>/dev/null)"
fi

export SSH_AUTH_SOCK


# 色を使用
autoload -Uz colors
colors

# 補完
autoload -Uz compinit
compinit

# emacsキーバインド
bindkey -e

# 他のターミナルとヒストリーを共有
#setopt share_history

# ヒストリーに重複を表示しない
setopt histignorealldups

HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000

# Ctrl+rでヒストリーのインクリメンタルサーチ、Ctrl+sで逆順
bindkey '^r' history-incremental-pattern-search-backward
bindkey '^s' history-incremental-pattern-search-forward

# コマンドを途中まで入力後、historyから絞り込み
# 例 ls まで打ってCtrl+pでlsコマンドをさかのぼる、Ctrl+bで逆順
autoload -Uz history-search-end
zle -N history-beginning-search-backward-end history-search-end
zle -N history-beginning-search-forward-end history-search-end
bindkey "^p" history-beginning-search-backward-end

# Gitのディレクトリにブランチ名を出す
autoload -Uz vcs_info
precmd_vcs_info() { vcs_info }
precmd_functions+=( precmd_vcs_info )
setopt prompt_subst
RPROMPT=\$vcs_info_msg_0_
# PROMPT=\$vcs_info_msg_0_'%# '
zstyle ':vcs_info:git:*' formats '%b'

PROMPT='%F{green}%n@%m%f:%F{blue}%~%f$ '

