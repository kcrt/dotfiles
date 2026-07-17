#!/bin/bash
# presentation_mode.sh — プレゼン時と通常時の設定を切り替える (macOS)
#
#   on / A     プレゼンモード:
#                - スクリーンセーバー: off
#                - ディスプレイオフ:   しない
#                - ホットコーナー:     全て off
#
#   off / B    通常モード:
#                - スクリーンセーバー: 5 分後に開始
#                - ディスプレイオフ:   10 分後
#                - ホットコーナー:     左下 = スクリーンセーバーを開始 (他は off)
#
#   toggle     現在の状態を見て自動で切り替える (引数省略時のデフォルト)
#
# ※ ディスプレイスリープの変更に pmset を使うため sudo パスワードを求められます。

set -euo pipefail

# --- ホットコーナーの値 (wvous-*-corner) ---
#  0: 何もしない   2: Mission Control   3: アプリケーションウインドウ
#  4: デスクトップ 5: スクリーンセーバーを開始   6: スクリーンセーバーを無効に
# 10: ディスプレイをスリープ  11: Launchpad  12: 通知センター  13: ロック画面

set_hot_corner() {
    # $1 = corner key (tl/tr/bl/br), $2 = action value, $3 = modifier value
    defaults write com.apple.dock "wvous-$1-corner"   -int "$2"
    defaults write com.apple.dock "wvous-$1-modifier" -int "$3"
}

enable_presentation() {
    echo "プレゼンモードに切り替えます…"

    # スクリーンセーバー: off (idleTime 0 = 開始しない)
    defaults -currentHost write com.apple.screensaver idleTime -int 0

    # ディスプレイオフ: しない (0 = never)
    sudo pmset -a displaysleep 0

    # ホットコーナー: 全て off
    set_hot_corner tl 0 0
    set_hot_corner tr 0 0
    set_hot_corner bl 0 0
    set_hot_corner br 0 0
    killall Dock

    echo "  スクリーンセーバー: off / ディスプレイオフ: しない / ホットコーナー: 全て off"
}

disable_presentation() {
    echo "通常モードに切り替えます…"

    # スクリーンセーバー: 5 分後 (300 秒)
    defaults -currentHost write com.apple.screensaver idleTime -int 300

    # ディスプレイオフ: 10 分後
    sudo pmset -a displaysleep 10

    # ホットコーナー: 左下 = スクリーンセーバーを開始、他は off
    set_hot_corner tl 0 0
    set_hot_corner tr 0 0
    set_hot_corner bl 5 0
    set_hot_corner br 0 0
    killall Dock

    echo "  スクリーンセーバー: 5分後 / ディスプレイオフ: 10分後 / ホットコーナー: 左下=スクリーンセーバー開始"
}

current_is_presentation() {
    # スクリーンセーバー idleTime が 0 ならプレゼンモード中とみなす
    local idle
    idle=$(defaults -currentHost read com.apple.screensaver idleTime 2>/dev/null || echo 300)
    [ "$idle" = "0" ]
}

mode="${1:-toggle}"
case "$mode" in
    on|On|ON|A|a)
        enable_presentation ;;
    off|Off|OFF|B|b)
        disable_presentation ;;
    toggle|Toggle|"")
        if current_is_presentation; then
            disable_presentation
        else
            enable_presentation
        fi ;;
    -h|--help|help)
        sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//' ;;
    *)
        echo "Usage: $(basename "$0") [on|off|toggle]" >&2
        exit 1 ;;
esac
