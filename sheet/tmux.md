# tmux 3.7   prefix = Ctrl+z (以下 ^z)   ★=直感的でない/画面に出ない

## 自前設定 (~/.tmux.conf = dotfiles/tmux/.tmux.conf、stow)
^z z    literal な Ctrl+z を送る=入れ子 tmux / ジョブ停止(suspend)★
^z ^z   直前のウィンドウへ★ | ^z Space 次ウィンドウ (既定の next-layout を潰している)★
^z hjkl ペイン移動 | ^z r 設定再読込 (既定は refresh-client)★ | mode-keys vi | mouse on
escape-time 50ms | history-limit 6000 行 (短め、長いログは早々に落ちる)★ | status-interval 1s

## WINDOW  ^z
c 新規 | , 改名 | & 閉じる(確認) | 0-9 番号選択 | ' index を入力して選択★ | n/p 次前
w ツリーから選択 | f 名前で検索(-Z)★ | . index を変更して移動★ | ! ペインを新ウィンドウへ切出し
M-n / M-p アラートの付いたウィンドウへ★ | M-1..7 レイアウト適用 | E 今のレイアウトで再配置★

## PANE  ^z
" 上下分割 / % 左右分割 (直感と逆になりがち)★ | x 閉じる(確認) | z ズーム | q 番号表示→数字で選択★
hjkl 移動(自前) | 矢印 移動 | o 次ペイン | ; 直前のペイン★ | { } 前後と入替 | ^o / M-o 回転★
^矢印 1 単位リサイズ | M-矢印 5 単位リサイズ | m マーク / M 解除 → join-pane 等の対象になる★
* フローティングペイン新規 (3.7〜、40x6 で浮く)★★ | Shift+矢印 端末より大きいウィンドウをパン★
> ペインのメニュー、< ウィンドウのメニュー (マウス右クリック相当)★

## COPY MODE  ^z [  (vi / ホイールでも入る)
移動 hjkl・w/b/e・0/^/$・g/G・H/M/L・{ } 段落 | ^u/^d 半画面・^b/^f 1画面・^e/^y 1行
検索 / ? → n/N | # / * カーソル下の語を後方/前方検索★ | : 行番号へジャンプ★
Space 選択開始 | v 矩形トグル(vi の visual ではない)★★ | V 行選択 | o 選択の反対端へ★
Enter or ^j コピーして抜ける | A 既存バッファへ追記★ | D 行末までコピー | q/^c 抜ける | Esc 選択解除のみ★
マウスでドラッグ→離した時点で自動コピー★ | ダブル/トリプルクリックで単語/行コピー★
set-clipboard 既定=external なので OSC52 対応端末なら OS のクリップボードにも入る★
^z ] 貼付 (-p ブラケットペースト)★ | ^z # バッファ一覧 | ^z = バッファ選択 | ^z - 直近バッファ削除

## SESSION / その他  ^z
d デタッチ | D クライアントを選んで切断★ | s セッションツリー | $ 改名 | ( ) 前後のセッション
L 直前のセッション★ | : コマンドプロンプト | ? キー一覧(説明付) | / キーを押してその説明を引く★
~ メッセージ履歴(エラーはここに残る)★ | t 時計 | C 設定 UI (customize-mode)★ | i ウィンドウ情報

## MOUSE (mouse on)
境界をドラッグでリサイズ | ステータスのウィンドウ名クリックで切替・ホイールで前後★
中クリックで貼付★ | ^クリックでペイン入替、ステータス上ならウィンドウ入替★
端末側 (iTerm2/Terminal.app) で普通に選択したい時は Option を押しながらドラッグ★

## CLI
tmux new -s NAME | tmux a [-t NAME] | tmux a -d 他クライアントを切離して接続★ | tmux ls
tmux kill-session -t NAME | tmux kill-server | tmux source ~/.tmux.conf
tmux new -d -s x 'cmd' でバックグラウンド実行、tmux send-keys -t x:0.1 'cmd' Enter で流し込み★
tmux capture-pane -p -S -6000 -t x:0.1 でペインの内容を標準出力へ★★
tmux display -p '#{pane_id}' 等でフォーマット評価★ | tmux display-popup -E -w 80% 'cmd'★
tmux new-pane 無指定=フローティング、-h/-v で分割★ | tmux -CC で iTerm2 ネイティブ統合★
$TMUX で在席判定 (中では TERM_PROGRAM=tmux)★

## この環境固有
status-left = user@host:session / status-right = script/cpuload.sh tmux + battery_info.sh
zsh 起動時: zellij があればそちらが優先され、tmux は zellij 不在時のみ `tmux ls` を表示★
  → dotfiles/zsh/.zshrc.d/860-terminal_multiplexer.zsh
900-hooks.zsh が TERM_PROGRAM=tmux のとき実行中コマンド名で rename-window する (自動改名)★
default-terminal screen-256color + terminal-overrides で truecolor とイタリックを有効化
