" -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
"
" .gvimrc
" 	kcrt http://profile.kcrt.net
"
" -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

scriptencoding utf-8

" ===== 設定 =====================================
set ch=2					" コマンドライン部の行数
set mousehide				" タイプ中にカーソルを隠す
set guioptions+=c			" メッセージボックスの代わりにコンソール選択を使う

" ===== フォントの設定 ===========================
" 最初に見つかったフォントから使用される
set guifont=FiraCode-Retina:h12,Menlo-Regular:h13,CourierNewPSMT:h13,Courier:h13,Consolas:h13
set guifontwide=HiraKakuProN-W3:h13,Osaka-Mono:h13,MS-Gothic:h13
if has('mac') && has('gui_running')
	set macligatures
endif

" ===== 印刷 =====================================
set printfont=HiraMinProN-W3:10,HiraginoMin-W3-90ms-RKSJ-H:h10
" use ^L for new page
set printoptions=left:20mm,right:20mm,top:10mm,bottom:15mm,header:3,formfeed:y
set printheader=%t(%{strftime('%Y/%m/%d\ %H:%M')})%=-%N-

" ===== ウィンドウの設定 ===================
"	ちょっと広め
set columns=90
set lines=27
if has('mac') && has('gui_running')
	set transparency=10
	autocmd FocusGained * set transparency=10
	autocmd FocusLost * set transparency=20
endif


" ===== IME使用時の設定 ==========================
if has('multi_byte_ime') || has('xim')
	highlight CursorIM guibg=Purple guifg=NONE
	set iminsert=0
	set imsearch=0
endif


" ===== Windowsヘルプの設定 ======================
if has("win32")
	let winhelpfile='d:\kt\Reference\Program\win32api\WIN32.HLP'
	au BufNewFile,BufRead *.cpp map K :execute "!start winhlp32 -k<cword> \"" . winhelpfile . "\"" <CR>
	au BufNewFile,BufRead *.c map K :execute "!start winhlp32 -k<cword> \"" . winhelpfile . "\"" <CR>
endif


" ===== キー設定 =================================
if has("win32")
	noremap <M-Space> :simalt ~<CR>
	inoremap <M-Space> <C-O>:simalt ~<CR>
	cnoremap <M-Space> <C-C>:simalt ~<CR>
	" F11で全画面モード
	map <silent> <F11> :if &guioptions =~# 'T' <Bar>
						 \simalt ~X<CR> <Bar> 
                         \set guioptions-=T <Bar>
                         \set guioptions-=m <Bar>
                         \set guioptions+=C <Bar>
						\else <Bar>
                         \set guioptions+=T <Bar>
                         \set guioptions+=m <Bar>
                         \set guioptions-=C <Bar>
						 \simalt ~R<CR> <Bar> 
				        \endif<CR>	
elseif has('mac')
	inoremap ¥ \
	inoremap \ ¥
endif

" ===== メニュー ================================
amenu &kcrt.&Update\ bundles	:BundleInstall!<CR>
amenu &kcrt.&Preview\ TeX		:PreviewTeX()<CR>
amenu &kcrt.&Char\ Count		:CharCount()<CR>
amenu &kcrt.&Convert\ to\ HTML	:call KcrtHTML()<CR>

function! KcrtHTML()
	set nonumber
	colorscheme morning
	runtime syntax/2html.vim
	w
	qall
endfunction
