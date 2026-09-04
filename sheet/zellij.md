# zellij 0.44   ★=直感的でない/画面に出ない

## MODE (Esc・Enter で normal / 同じ Ctrl+x でも解除)
Ctrl+p pane | Ctrl+t tab | Ctrl+n resize | Ctrl+h move | Ctrl+s scroll | Ctrl+o session
Ctrl+b tmux互換 | Ctrl+q 終了 | Ctrl+g locked★ 全バインド無効=入れ子zellij/vimへキーを渡す

## ALT (モード切替不要)
Alt+h/l 移動、端でタブを跨ぐ★ | Alt+j/k 上下(跨がない) | Alt+n 新ペイン | Alt+f floating
Alt+i/o タブ自体を左/右へ★ | Alt+[/] swap layout 巡回(要 swap 定義)★ | Alt+=/- 拡大縮小
Alt+p グループに追加/解除★ | Alt+Shift+p グループマーキング★

## PANE  Ctrl+p
hjkl 移動 | n/d/r 新規(自動/下/右) | s stacked★ | p 次へ | x 閉 | f 全画面 | c 改名
w floating表示 | e embed⇔floating 入替★ | i floating を最前面に pin★ | z 枠表示(コピペ用)★

## TAB  Ctrl+t
hjkl・1-9 移動 | Tab 直前のタブへ★ | n/x/r 新規/閉/改名 | s sync=タブ内全ペインに同入力★
b ペインを新タブへ切り出し★ | [ / ] ペインを左/右のタブへ移動★

## RESIZE Ctrl+n / MOVE Ctrl+h
resize: hjkl その方向へ広げる | HJKL(Shift) 縮める★ | +/- 全体 | 縮め過ぎると自動スタック化★
move:   hjkl 位置を入替 | n・Tab 次の位置 | p 逆方向★

## SCROLL  Ctrl+s
j/k 行 | h/l・PgUp/Dn ページ | d/u 半ページ★ | Ctrl+c 最下部へ戻って normal★
e スクロールバックを $EDITOR で開く★★ | s 検索 → n/p 次前, c 大小, w wrap, o 単語★

## SESSION Ctrl+o / TMUX Ctrl+b (ワンショット)
d detach★(Ctrl+q は終了) | w セッション切替・終了済みの復活★ | c 設定UI | p プラグイン管理
tmux: "/% 下/右分割 | c 新タブ | o 次ペイン | n/p タブ | , 改名 | z 全画面 | [ scroll | d detach
Ctrl+b Ctrl+b で literal な Ctrl+b を送る★

## CLI
zellij a -c NAME 無ければ作って attach★ | zellij ls EXITED も表示→attach で復活★
zellij d NAME 復活データごと削除★ | zellij run -f -- CMD | zellij edit FILE
zellij action dump-screen F --full★ / rename-tab / go-to-tab-name / new-pane -d right
$ZELLIJ で在席判定★ | 設定 ~/dotfiles/zellij/.config/zellij/{config,layouts/{default,agents}}.kdl
zellij-agents  上 agent-view 30% / 下 田の字 4 枚 で新セッション (ZELLIJ_NO_TAB_RENAME=1 付き)
レイアウトが端末に入らないと zellij は無言で即終了★ 固定行指定(size=10 等)は要求高さが激増する
-l/--layout はセッション内だと新セッションでなく今のセッションにタブを足す★ -n なら必ず新規
swap layout の max_panes/min_panes は plugin ペイン (zjstatus/status-bar) も数える→実ペイン数 +2★★

## 枠タイトル (ペインタイトル)  ★★
優先順 name= (layout / Ctrl+p → c) > OSC 0/2 > コマンド行・Pane #N
name= を付けると固定表示。中身に追従させたいペインは名前を付けない★
command 付きペインはコマンド行に固定され OSC で上書きできない★
set_title は zellij 配下でタブ名も改名する→複数ペインのタブは ZELLIJ_NO_TAB_RENAME=1 で抑止
