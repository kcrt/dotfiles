# NetHack 5.0.0 (brew)   ★=直感的でない/画面に出ない

## 移動  (既定 number_pad:0)
hjkl yubn 1歩 | HJKL YUBN その方向へ run | Ctrl+同じ文字 rush★
g<dir> = rush 前置 / G<dir> = run 前置 (大文字と Ctrl はその短縮形)
5.0 で M<dir> は廃止された★★ | ^L は再描画ではなく「東へ rush」★★ 再描画は ^R
Enter (=^J) は「南へ rush」。メニューの癖で押すと走り出す★★
m<dir> 拾わず攻撃せず進む | F<dir> 見えていない相手にも攻撃 (#fight)
_ travel カーソルで目的地を指して最短路 | ^_ 前回の travel 先へ再実行★
数字はカウント。20s で s を 20 回★ | < > 階段 | . 1ターン待つ | ^A 直前コマンドを再実行

## アイテム・装備
i 持ち物 / I クラス指定 | , 拾う / @ autopickup トグル | d 捨てる / D 種類指定
w 武器 (w- で素手に戻す)★ | W 防具 / P 装飾品 | T 防具を外す / R 装飾品を外す
A 全部まとめて外す★ | x 主武器と予備を入替 / X 二刀流トグル
a 道具を使う | q 飲む | r 読む | e 食べる | E 床に刻む | t 投げる
f quiver から射つ / Q quiver を選ぶ★ ゲーム終了は #quit であって Q ではない★★
z 杖 / Z 呪文 | + 呪文一覧と並べ替え | \ 既知アイテム全部 / ` クラス別★
) [ = " ( 使用中の 武器/防具/指輪/護符/道具 | * まとめて | $ 所持金

## 情報・ユーティリティ
: 足元 | ; 離れた1マスを説明 (#glance) | / 記号から引く (#whatis) | ^ 隣の既知の罠★
^X 能力値 | ^P 直前のメッセージ (連打で遡る)★ | ^O 探索済み階層の要約★
v = #chronicle 重要イベントの年代記 (5.0 新)★★  V は版番号の表示★
S セーブして終了。「セーブして続行」は存在しない★ | #quit 保存せず終了
O 簡易オプション / mO (=#optionsfull) 全オプション★ | #saveoptions 現設定を書き出す★
! サブシェル (exit で戻る) | ^Z 中断 → fg で復帰 | #bugreport ブラウザで報告★

## m 前置 = reqmenu★★
m は「移動の前置」と「コマンドをメニュー版にする前置」を兼ねる (mO, m, など)
#? の一覧で [m] が付く物が m 前置に対応、[A] が付く物は名前補完が効く★

## メニュー操作キー★★
選択 . 全体 / , 現ページ | 反転 @ / ~ | 解除 - / \
ページ > 次 / < 前 / ^ 先頭 / | 末尾 | : 文字列を入れて一致行を反転★
Return 確定 | Space 次ページ、最終ページなら確定★ | Esc 取消

## 拡張コマンド ( # に続けて入力、# ? で全一覧 )
#pray #offer #sit #chat #loot #tip #untrap #force #dip #rub #jump #ride #turn #wipe
#invoke #adjust #annotate #enhance #conduct #genocided #vanquished #overview #name
#terrain 地形だけ表示★ | #herecmdmenu / #therecmdmenu 今ここで出来る事のメニュー★
#lookaround 見えている物の説明★ | #perminv (キー | ) 常設インベントリをスクロール★
#version compile 時オプション / #history 開発史 / #versionshort (=V)
Terminal.app・iTerm2 は Meta を送らないので M-p 等は素で効かない★
 → OPTIONS=altmeta を入れて Esc→p、または端末側で Option を Meta にする。#pray と打つのが確実

## 定石
Elbereth: E - Elbereth と床に刻む。多くの敵が逃げる。自分が攻撃すると消える
#pray は HP が 1/7 未満・餓死寸前などの「困窮」時のみ。連発すると神が怒る (間隔の目安 1000 ターン)
腐った死体は食べない | 未鑑定品は店の値段で推定 (price ID) | 祭壇に落とすと BUC が分かる★
ペットが踏むのを避けたアイテムは呪われている★
Dlvl に対して経験値が足りない「潜り過ぎ」が最大の死因。急がず稼ぐ
Sokoban は Oracle から上り、Gnomish Mines は下り。Mine Town に店・神殿・祭壇
