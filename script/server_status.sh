#!/bin/zsh

# サーバー状況を1文字で表示する。実体は beryllium の中継 (signal-tower-relay)。
# 中継は Grafana Cloud のアラートを G/I/W/A/U/? の1行に潰している。
#   param
#       zjstatus - zjstatus のステータスバー用に色を付ける
#   なし     - 中継の生の1行をそのまま出す

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Usage: $(basename "$0") [zjstatus]"
    echo "Shows the server status light (green/info/warn/alert/urgent) from the home relay."
    exit 0
fi

RELAY_LAN="${SIGNAL_RELAY_URL:-http://192.168.15.13:13004/}"   # beryllium。宅内から直接（テスト時は SIGNAL_RELAY_URL で差し替え）
RELAY_HOST="${SIGNAL_RELAY_HOST:-home.kcrt.net}"              # 外からは ssh 越しに取る（テスト時は SIGNAL_RELAY_HOST で差し替え）
CACHE="${TMPDIR:-/tmp}/server_status.cache"
CACHE_GRACE=90                              # 取得に失敗しても、この秒数までは前回値で表示する
ROUTE="${TMPDIR:-/tmp}/server_status.route" # 前回成功した経路 (lan / ssh)

via_lan() {
    curl -s --connect-timeout 0.6 --max-time 1.5 "$RELAY_LAN" 2>/dev/null
}

via_ssh() {
    # ControlPersist でコネクションを使い回す。毎回ハンドシェイクすると15秒間隔には重い。
    ssh -o BatchMode=yes -o ConnectTimeout=3 \
        -o ControlMaster=auto -o ControlPath="${TMPDIR:-/tmp}/ssh-signal-%r@%h:%p" -o ControlPersist=10m \
        "$RELAY_HOST" 'curl -s --max-time 2 http://localhost:13004/' 2>/dev/null
}

fetch_status() {
    # 前回成功した経路を先に試す。宅外で毎回 LAN の 0.6 秒を空振りしないため。
    local first=lan second=ssh
    [[ -f "$ROUTE" && "$(<"$ROUTE")" == ssh ]] && { first=ssh; second=lan; }
    local result
    for route in $first $second; do
        result=$(via_$route)
        if [[ -n "$result" ]]; then
            print -rn -- "$route" > "$ROUTE"
            print -r -- "$result"
            return 0
        fi
    done
    return 1
}

line=$(fetch_status)
if [[ -n "$line" ]]; then
    print -r -- "$line" > "$CACHE"
elif [[ -f "$CACHE" ]]; then
    # 1回きりの取りこぼしでバーがちらつかないよう、少しだけ前回値を使う。
    cache_age=$(( $(date +%s) - $(stat -f %m "$CACHE" 2>/dev/null || stat -c %Y "$CACHE") ))
    (( cache_age <= CACHE_GRACE )) && line=$(<"$CACHE")
fi

level="${line[1]}"
[[ -z "$line" ]] && level="?"
top="${line#*top=}"
[[ "$top" == "$line" ]] && top=""
[[ "$line" == *degraded=1* ]] && top="!${top}"
(( ${#top} > 28 )) && top="${top[1,27]}…"
count="${line#*n=}"; count="${count%% *}"
[[ "$line" != *n=* ]] && count=""

if [[ "$1" != "zjstatus" ]]; then
    print -r -- "${line:-? (relay unreachable)}"
    exit 0
fi

case "$level" in
    G) print -r -- "#[fg=#3DB88B]●" ;;
    I) print -r -- "#[fg=#3DB88B]● ${count}" ;;
    W) print -r -- "#[fg=#E28C36]● ${top}" ;;
    A) print -r -- "#[fg=#d74242]● ${top}" ;;
    U) print -r -- "#[bg=#d74242, fg=#F5E0E0]● ${top}" ;;
    *) print -r -- "#[fg=#6C7086]○ ?" ;;
esac
