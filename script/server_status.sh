#!/bin/zsh

# サーバー状況を1文字で表示する。実体は beryllium の中継 (signal-tower-relay)。
# 中継は Grafana Cloud のアラートを G/I/W/A/U/? の1行に潰している。
#   param
#       zjstatus - zjstatus のステータスバー用に色を付ける
#   なし     - 中継の生の1行をそのまま出す
#
# 取れなかったときは原因を3つに分ける。対処が違うため。
#   offline - 自分がネットワークに繋がっていない (灰。こちらの問題なのでバーは静かに)
#   host    - ネットはあるが家まで届かない。宅内なら beryllium 本体が黙っている (橙)
#   relay   - beryllium は応答するが中継だけ死んでいる (橙。中継を起こせば直る)

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Usage: $(basename "$0") [zjstatus]"
    echo "Shows the server status light (green/info/warn/alert/urgent) from the home relay."
    echo "When it cannot be fetched, tells offline / host unreachable / relay down apart."
    exit 0
fi

RELAY_LAN="${SIGNAL_RELAY_URL:-http://192.168.15.13:13004/}"   # beryllium。宅内から直接（テスト時は SIGNAL_RELAY_URL で差し替え）
RELAY_HOST="${SIGNAL_RELAY_HOST:-home.kcrt.net}"              # 外からは ssh 越しに取る（テスト時は SIGNAL_RELAY_HOST で差し替え）
CACHE="${TMPDIR:-/tmp}/server_status.cache"
CACHE_GRACE=90                              # 取得に失敗しても、この秒数までは前回値で表示する
ROUTE="${TMPDIR:-/tmp}/server_status.route" # 前回成功した経路 (lan / ssh)
SSH_ERR="${TMPDIR:-/tmp}/server_status.ssherr"

line=""         # 中継から取れた1行
fail=""         # 取れなかった理由 (offline / host / relay)
lan_status=0    # try_lan の終了コード。7 は相手が RST を返した = ホストは生きている印
ssh_status=0    # try_ssh の終了コード。255 は ssh 自体が繋がらなかった印

have_default_route() {
    # 経路表を見るだけなので、ネットワークに触らず即答する。到達性までは問わない。
    if [[ "$OSTYPE" == darwin* ]]; then
        route -n get default > /dev/null 2>&1
    elif (( $+commands[ip] )); then
        [[ -n "$(ip route show default 2>/dev/null)" ]]
    else
        return 0    # 判定できない環境では「ある」側に倒し、offline を名乗らない
    fi
}

try_lan() {
    line=$(curl -s --connect-timeout 0.6 --max-time 1.5 "$RELAY_LAN" 2>/dev/null)
    lan_status=$?
    [[ -n "$line" ]]
}

on_relay_lan() {
    # 自分の IPv4 が中継と同じ /24 にいるか = 宅内にいるか。
    # 宅内では LAN の失敗の仕方が一番確かな手掛かりになるので、その重み付けに使う。
    local host="${${RELAY_LAN#*://}%%[:/]*}"
    [[ "$host" == <->.<->.<->.<-> ]] || return 1    # ホスト名で指定されていたら判定できない
    if [[ "$OSTYPE" == darwin* ]]; then
        ifconfig 2>/dev/null | grep -qF "inet ${host%.*}."
    else
        ip -4 -o addr show 2>/dev/null | grep -qF "inet ${host%.*}."
    fi
}

try_ssh() {
    # ControlPersist でコネクションを使い回す。毎回ハンドシェイクすると15秒間隔には重い。
    # 終了コード 255 は ssh 自体が繋がらなかった印。それ以外は向こうの curl の終了コードが
    # そのまま返るので、beryllium は生きていて中継だけ死んでいると分かる。
    line=$(ssh -o BatchMode=yes -o ConnectTimeout=3 \
        -o ControlMaster=auto -o ControlPath="${TMPDIR:-/tmp}/ssh-signal-%r@%h:%p" -o ControlPersist=10m \
        "$RELAY_HOST" 'curl -s --max-time 2 http://localhost:13004/' 2> "$SSH_ERR")
    ssh_status=$?
    [[ -n "$line" ]]
}

classify_failure() {
    # ssh の終了コードと言い分から原因を決める。心当たりが無いときは家のせいにせず ? に落とす
    # (ControlPath が長すぎる等、こちらの設定が壊れていても ssh は 255 を返してくる)。
    local err="$(<"$SSH_ERR")"
    if (( lan_status == 7 )) && on_relay_lan; then
        # 宅内から繋いで RST が返った。beryllium は生きていて中継だけ黙っている。
        # 宅外へ出る経路 (hairpin NAT 等) の都合より、この手掛かりの方が確か。
        print -rn -- relay
    elif [[ "$err" == *resolve* || "$err" == *"not known"* ]]; then
        print -rn -- offline    # 名前が引けない。既定経路はあってもネットは死んでいる
    elif (( ssh_status != 255 )); then
        print -rn -- relay      # ssh は通った = beryllium は生きていて中継だけ黙っている
    elif [[ "$err" == *"No route to host"* || "$err" == *"Network is unreachable"* ]]; then
        print -rn -- offline    # 経路表にはあるが実際には出ていけない
    elif [[ "$err" == *"timed out"* || "$err" == *refused* || "$err" == *"Connection closed"* \
            || "$err" == *"reset by peer"* || "$err" == *"broken pipe"* ]]; then
        print -rn -- host
    fi
}

fetch_status() {
    if ! have_default_route; then
        # 既定経路が無いなら ssh の3秒を待つだけ無駄。LAN だけ試して諦める。
        try_lan && return 0
        fail=offline
        return 1
    fi
    # 前回成功した経路を先に試す。宅外で毎回 LAN の 0.6 秒を空振りしないため。
    local first=lan second=ssh
    [[ -f "$ROUTE" && "$(<"$ROUTE")" == ssh ]] && { first=ssh; second=lan; }
    for route in $first $second; do
        if try_$route; then
            print -rn -- "$route" > "$ROUTE"
            return 0
        fi
    done
    fail=$(classify_failure)
    return 1
}

fetch_status
if [[ -n "$line" ]]; then
    print -r -- "$line" > "$CACHE"
elif [[ -f "$CACHE" ]]; then
    # 1回きりの取りこぼしでバーがちらつかないよう、少しだけ前回値を使う。
    cache_age=$(( $(date +%s) - $(stat -f %m "$CACHE" 2>/dev/null || stat -c %Y "$CACHE") ))
    (( cache_age <= CACHE_GRACE )) && { line=$(<"$CACHE"); fail="" }
fi

level="${line[1]}"
[[ -z "$line" ]] && level="?"
top="${line#*top=}"
[[ "$top" == "$line" ]] && top=""
(( ${#top} > 28 )) && top="${top[1,27]}…"
count="${line#*n=}"; count="${count%% *}"
[[ "$line" != *n=* ]] && count=""
# 取得元の片方が鮮度切れ。どのレベルでも「平常の顔」をさせないよう ! を前置する。
mark=""
[[ "$line" == *degraded=1* ]] && mark="!"

# 取れなかった理由ごとの見た目と文言
case "$fail" in
    offline) fail_color="#6C7086"; fail_label="offline";    fail_text="offline (no network from here)" ;;
    host)    fail_color="#E28C36"; fail_label="home?";      fail_text="cannot reach home ($RELAY_LAN / $RELAY_HOST)" ;;
    relay)   fail_color="#E28C36"; fail_label="relay?";     fail_text="relay down on beryllium" ;;
    *)       fail_color="#6C7086"; fail_label="?";          fail_text="relay unreachable" ;;
esac

if [[ "$1" != "zjstatus" ]]; then
    print -r -- "${line:-? ($fail_text)}"
    exit 0
fi

case "$level" in
    G) print -r -- "#[fg=#3DB88B]●${mark:+ !}" ;;
    I) print -r -- "#[fg=#3DB88B]● ${mark}${count}" ;;
    W) print -r -- "#[fg=#E28C36]● ${mark}${top}" ;;
    A) print -r -- "#[fg=#d74242]● ${mark}${top}" ;;
    U) print -r -- "#[bg=#d74242, fg=#F5E0E0]● ${mark}${top}" ;;
    *) print -r -- "#[fg=${fail_color}]○ ${fail_label}" ;;
esac
