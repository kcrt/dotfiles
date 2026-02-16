
" -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
"
" .vimrc
" 	kcrt http://profile.kcrt.net
"
" -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

scriptencoding utf-8
set encoding=utf-8
set termencoding=utf-8
set nocompatible				" 拡張機能を有効にする
set modeline
set number

" ----- 最初から入ってる奴 -----------------------
syntax on
filetype plugin indent on
augroup vimrcEx
  autocmd!
  " 開いたらとりあえず前のカーソルの位置へ
  autocmd BufReadPost *
    \ if line("'\"") > 0 && line("'\"") <= line("$") |
    \   exe "normal g`\"" |
    \ endif
augroup END

" ===== システムに関する設定 =====================
if has("win32")
	" let $HOME="d:\\kt"
endif

" ===== ユーザーインターフェース関係 =============
" ----- 設定 -------------------------------------
set backspace=2					" <BS>の動作設定
set history=50					" :コマンドの履歴数
set showcmd						" コマンド表示
set laststatus=2				" 最下部情報行の行数
set statusline=%h%w%f\ %m%#RO#%r%#StatusLine#%y%{'['.(&fenc!=''?&fenc:&enc).']['.&ff.']'}%=%4v\ %l/%L\ (%p%%)
set scrolloff=3					" スクロール時に3行表示
set ttyfast
set nrformats=bin,hex,alpha
" ----- マウス -----------------------------------
if stridx(&term, "screen") != -1
	set mouse=a					" マウス有効
	set ttymouse=xterm2
endif
" ----- タブインターフェース(またはバッファ) -----
map Q gq
" C-Tabでタブが使えるときはタブを切り替え
" 使えない場合はバッファの切り替えを行う
" if(exists(":tab"))
" 	nmap <C-Tab>		:tabn<CR>
" 	nmap <C-S-Tab>		:tabprev<CR>
" else
" 	nmap <C-Tab>		:bn<CR>
" 	nmap <C-S-Tab>		:bp<CR>
" endif
" タブラインの表記
set tabline=%!MyTabLine()	"後述
set showtabline=2			" 常にタブを表示


" ----- コマンド略記------------------------------
ca man help

" ----- 補完 -------------------------------------
set complete =.,w,k,b,u,t,i
set wildmenu
set wildmode=list,full
if (exists('*pumvisible') && has("gui"))
	" inoremap <expr> <CR> pumvisible() ? "\<c-y>" : "\<c-g>u\<cr>"
	" inoremap <expr> <Esc> pumvisible() ? "\<C-E>":"\<Esc>"
endif
" C-Spaceに対してomniが使用可能なら使う、無理なら通常の<C-N>
" 一部の環境ではCtrl+Spaceが<Nul>として入力される
if (exists('&omnifunc'))
	imap <C-Space> <C-X><C-O>
	imap <Nul> <C-X><C-O>
	iabbrev </ </<C-X><C-O>
else
	imap <C-Space> <C-N>
	imap <Nul> <C-N>
endif
" ----- キーの動作に関する設定 -------------------
set whichwrap=[,],>,<,b,s		" 行末でLeft/Right 押しても次の行へ
" ----- その他のキー設定 -------------------------
set timeout timeoutlen=100 ttimeoutlen=100
map <F1> K
map K \K
" map <Esc>[A <Up>
" map <Esc>[B <Down>
" map <Esc>[C <Right>
" map <Esc>[D <Left>
inoremap jjj <ESC>jjj
nnoremap <UP> gk
nnoremap <DOWN> gj
nnoremap ：ｗ :w<CR>:echoe "File saved, but your input method manager is ON!"<CR>
if has("nvim")
	tnoremap <C-w> <C-\><C-n><C-w>
	tnoremap <C-w><C-w>		<C-\><C-n>
endif


" ===== 編集に関連する設定 =======================
" ----- 文字エンコードの設定 ---------------------
set fileencodings=utf-8,shift_jis,euc-jp
set fileencoding=utf-8			" デフォルトのファイルエンコーディング
set ambiwidth=single			" 幅未定義MBSCの幅
" テスト用: abcdａｂｃｄαβγδ・:○◎×本日は晴天なり
" テスト用: [○][〇][🍎]
" ----- 親切設定 ---------------------------------
set showmatch					" 対応する括弧を強調表示
set matchpairs+=「:」,『:』,（:）,【:】,《:》,〈:〉,［:］,‘:’,“:”
set display=lastline			" @@@表示
" テスト用: Formerly most Japanese houses were made of wood. You look pale.  What is the matter with you? I've got a pain in my stomach. That's too bad.  The riches are not always happier than the poor.
" ----- 検索 -------------------------------------
set incsearch					" インクリメンタルサーチ
set hlsearch					" 検索時ハイライト有効
if has("nvim")
	set inccommand=split
endif
set ignorecase					" 検索時大文字・小文字無効
set smartcase					" 検索時大文字・小文字自動判別
" 見つかったアイテムを自動的に中央に
nmap n nzz
nmap N Nzz
" ----- タブとインデント -------------------------
set tabstop=4					" <Tab>に対応する空白数
set shiftwidth=4				" インデントに使われる空白数
set softtabstop=4				" タブとして使われる空白数
set autoindent					" 自動インデント
set smartindent					" スマートインデント
autocmd FileType python :set expandtab
autocmd FileType dart :set expandtab
autocmd FileType dart :set shiftwidth=2
autocmd FileType dart :set tabstop=2
autocmd FileType dart :set softtabstop=2
autocmd FileType typescript.tsx :set expandtab
autocmd FileType typescript.tsx :set shiftwidth=2
autocmd FileType typescript.tsx :set tabstop=2
autocmd FileType typescript.tsx :set softtabstop=2
autocmd FileType markdown :set expandtab

" ===== 動作設定 =================================
" ----- バックアップ -----------------------------
set backup						" バックアップ有効
if has("win32")
	set backupdir& backupdir=$HOME/Backup
else
	set backupdir& backupdir=$HOME/.backup
endif
" crontab はbackup無効にする。
autocmd BufRead /tmp/crontab.* :set nobackup nowritebackup

" ----- クリップボード ---------------------------
nnoremap x "_x
imap <C-R>*	<C-O>"*p
nmap "*yy	V"*y
if has("win32unix")				" cygwinの事です
	nnoremap "*p :r!getclip<CR>
	vnoremap "*y :!putclip<CR>u:echo 'copyed'<CR>
elseif has("mac")
	" do nothing. everything will work.
elseif has("unix")
	if $TERM=~"screen.*"
		nnoremap "*p	:!screen -X writebuf ~/tmp/vim-clipboard<CR>:r ~/tmp/vim-clipboard<CR>
		vnoremap "*y	:w! ~/tmp/vim-clipboard<CR>:!screen -X readbuf ~/tmp/vim-clipboard<CR>:echo 'copyed'<CR>
	else
		nnoremap "*p	:r ~/tmp/vim-clipboard<CR>
		vnoremap "*y	:w! ~/tmp/vim-clipboard<CR>:echo 'copyed'<CR>
	endif
endif
autocmd InsertLeave * set nopaste

" ----- 差分 -------------------------------------
set diffopt+=algorithm:patience,indent-heuristic


" ----- screen関係の設定 -------------------------
if &term =~ "screen.*"
	augroup IsTerminal
		autocmd!
		autocmd VimLeave * silent! exe '!echo -n "\ek' .  &shell . '\e\\"'
		autocmd BufEnter * silent! exe '!echo -n "\ek' . "vim:%:t" . '\e\\"'
	augroup END
endif


" ===== 印刷設定 =================================
" set printfont="ヒラギノ"	-> gvimrc


" ===== ファイル関連設定 =========================
" ----- テンプレート -----------------------------
augroup LoadTemplate
	autocmd!
	let templatefiles = split(glob('~/dotfiles/template/*'), '\n')
	for filename in templatefiles
		let f = matchlist(filename, '.*\.\(.*\)')
		let ext = f[1]
		execute 'autocmd BufNewFile *.' . ext . ' 0r ~/dotfiles/template/template.' . ext
	endfor
augroup END

" ----- ファイル別設定 ---------------------------
augroup filetypedetect
	"autocmd! こいつだけは上書きできない
	autocmd BufNewFile,BufRead *.txt :setf txt
	autocmd BufNewFile,BufReadPre *.howm :set fileformats=dos,unix
	autocmd BufNewFile,BufReadPost *.pl :set filetype=perl
	autocmd BufNewFile,BufReadPost *.pm :set filetype=perl
	autocmd BufNewFile,BufReadPost *.ctp :set filetype=php
	autocmd BufNewFile,BufReadPost *.r :set filetype=r
	autocmd BufNewFile,BufReadPost *.wsgi :set filetype=python
	autocmd BufNewFile,BufReadPost *.jl :set filetype=julia
	" F5で実行
	autocmd BufNewFile,BufRead *.pl :map <F5> :QuickRun<CR>
	autocmd BufNewFile,BufRead *.php :map <F5> :QuickRun<CR>
	autocmd BufNewFile,BufRead *.cpp :map <F5> :QuickRun<CR>
	autocmd BufNewFile,BufRead *.R :map <F5> :QuickRun<CR>
	autocmd BufNewFile,BufRead .vimrc :map <F5> :source %:p<CR>
	autocmd BufNewFile,BufRead *.tex :map <F5> :call PreviewTeX()<CR>
	autocmd BufNewFile,BufRead *.sh :map <F5> :! %:p<CR>
	" F7 で構文チェックとか
	autocmd BufNewFile,BufRead *.pl :map <F7> :!perl -cw%:p<CR>
	" 折りたたまれないように
	autocmd FileType git :setlocal foldlevel=99
	autocmd FileType gitcommit :setlocal spell
	" 自動で日付を書く
	autocmd BufRead diary.txt :$r! LANG=C date "+\%n\%Y-\%m-\%d \%a \%H:\%M:\%S\%n"
augroup END
let php_baselib = 1
let php_htmlInString = 1
let php_folding = 1

" ----- 暗号化 -----------------------------------
if !has("nvim")
	if has("patch-7.4-399")
		set cryptmethod=blowfish2
	else
		set cryptmethod=blowfish
	endif
endif

" ----- 折りたたみ -------------------------------
set foldmethod=indent
set foldlevel=99

" ----- バイナリファイル編集 ---------------------
"  see :help xxd
augroup Binary
	au!
	autocmd BufReadPost * if &binary | exe ":%!xxd -g 1" | set ft=xxd | endif
	autocmd BufWritePre * if &binary | exe ":%!xxd -r" | endif
	autocmd BufWritePost * if &binary | exe ":%!xxd -g 1" | set nomod | endif
augroup END

" ===== プラグイン設定 ===========================
" ----- vim-plug ---------------------------------
if !filereadable(expand("~/.vim/autoload/plug.vim"))
	echo "You need to install vim-plug!"
	echo "Please execute: curl -fLo ~/.vim/autoload/plug.vim --create-dirs https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim"
	command -nargs=* Plug echo
endif
call plug#begin('~/.vim/plugged')
" --- vim enviroment
" Plug 'sudo.vim'						" Enable vi sudo:file.txt
Plug 'tpope/vim-surround'				" Enable additional text-object like s(
" --- color scheme
Plug 'w0ng/vim-hybrid'				" Good color scheme based on Solarized
Plug 'vim-scripts/AnsiEsc.vim'		" apply escape sequense like: <Esc>[36mHello<Esc>[0m , :AnsiEsc
Plug 'chrisbra/Colorizer'				" :ColorHighLight
" --- Encryption
Plug 'jamessan/vim-gnupg'
" --- development
Plug 'thinca/vim-quickrun'
Plug 'scrooloose/nerdtree'
Plug 'jistr/vim-nerdtree-tabs'
Plug 'majutsushi/tagbar'
Plug 'luochen1990/rainbow'
Plug 'rhysd/devdocs.vim'
Plug 'editorconfig/editorconfig-vim'
" --- Language server protocol
Plug 'prabirshrestha/async.vim'
Plug 'prabirshrestha/vim-lsp'
Plug 'prabirshrestha/asyncomplete.vim'
Plug 'prabirshrestha/asyncomplete-lsp.vim'
Plug 'mattn/vim-lsp-settings'
" --- git
Plug 'gregsexton/gitv'
Plug 'tpope/vim-fugitive'
Plug 'airblade/vim-gitgutter'
Plug 'Xuyuanp/nerdtree-git-plugin'
Plug 'hotwatermorning/auto-git-diff'
" --- julia
Plug 'JuliaEditorSupport/julia-vim'
" --- go
" --- LaTeX
Plug 'lervag/vimtex'
" --- HTML
Plug 'gregsexton/MatchTag'		" Highlight matched html/xml tag
Plug 'othree/html5.vim'
Plug 'alvan/vim-closetag'
" --- JavaScript
Plug 'MaxMEllon/vim-jsx-pretty'				" JSX highlight
Plug 'moll/vim-node'
Plug 'othree/es.next.syntax.vim'				" ES Stage-9 syntax highlight
Plug 'othree/javascript-libraries-syntax.vim'
Plug 'othree/yajs.vim'						" ES6 Highlight
Plug 'pangloss/vim-javascript'
" --- Dart, flatter
Plug 'dart-lang/dart-vim-plugin'
" --- TypeScript
Plug 'leafgarland/typescript-vim'
Plug 'peitalin/vim-jsx-typescript'
" --- CSV
Plug 'mechatroner/rainbow_csv'
" --- Other programming
Plug 'jalvesaq/Nvim-R'
Plug 'tpope/vim-endwise'
Plug 'sudar/vim-arduino-syntax'
" --- Japanese
Plug 'haya14busa/vim-migemo'
Plug 'fuenor/JpFormat.vim'
" --- Copilot
Plug 'https://github.com/github/copilot.vim'

call plug#end()


" ----- QuickRun -------------------
" use clang and C++11 for default, if available
let g:quickrun_config = {}
if executable("clang++")
	let g:quickrun_config['cpp/clang++11'] = {'cmdopt': '-O --std=c++11 --stdlib=libc++', 'type': 'cpp/clang++'}
	let g:quickrun_config['cpp/clang++14'] = {'cmdopt': '-O --std=c++14 --stdlib=libc++', 'type': 'cpp/clang++'}
	let g:quickrun_config['cpp/clang++17'] = {'cmdopt': '-O --std=c++17 --stdlib=libc++', 'type': 'cpp/clang++'}
	let g:quickrun_config['cpp'] = {'type': 'cpp/clang++17'}
endif
" javascript and jsx
let $NODE_ENV="development"
let g:vim_jsx_pretty_colorful_config = 1
let g:used_javascript_libs = 'react,redx'
let b:javascript_lib_use_react = 1
" typescript
autocmd BufNewFile,BufRead *.tsx,*.jsx set filetype=typescript.tsx
" haskell
if executable("stack")
	let g:quickrun_config['haskell'] = {'command': 'stack', 'cmdopt': 'runghc'}
endif
" go
let g:go_version_warning = 0
" R
let vimrplugin_assign=0
" dart
let g:dart_format_on_save = 1

" ----- LSP --------------------------------------
let g:lsp_signs_enabled = 1
let g:lsp_diagnostics_echo_cursor = 1
let g:lsp_signs_error = {'text': '✗', 'icon': expand('~/dotfiles/materials/image/lsp_error.png')}
let g:lsp_signs_warning = {'text': '‼', 'icon': expand('~/dotfiles/materials/image/lsp_warning.png')}
let g:lsp_signs_information = {'text':'ℹ', 'icon': expand('~/dotfiles/materials/image/lsp_information.png')}
let g:lsp_signs_hint = {'text':'ℹ', 'icon': expand('~/dotfiles/materials/image/lsp_information.png')}

" Use ruff for Python LSP instead of pylsp
let g:lsp_settings_filetype_python = ['ruff']

" Alert if ruff is not installed when opening Python files
augroup CheckRuffInstalled
  autocmd!
  autocmd FileType python if !executable('ruff') | echohl WarningMsg | echom "Warning: ruff LSP not found. Install with: uv tool install ruff" | echohl None | endif
augroup END

" ----- NERDTree ---------------------------------
let NERDTreeShowHidden = 1
let g:NERDTreeIgnore = ['\.pyc$']
let g:NERDTreeDirArrows = 1
let g:nerdtree_tabs_open_on_gui_startup = 1
let g:nerdtree_tabs_open_on_new_tab = 1

" ----- その他のプラグイン -----------------------
runtime ftplugin/man.vim
runtime macros/matchit.vim
let g:rainbow_active = 1
let g:rainbow_conf = {
\	'guifgs': ['royalblue3', 'darkorange3', 'seagreen3', 'firebrick'],
\	'ctermfgs': ['lightblue', 'lightyellow', 'lightcyan', 'lightmagenta'],
\	'operators': '_,_',
\	'parentheses': ['start=/(/ end=/)/ fold', 'start=/\[/ end=/\]/ fold', 'start=/{/ end=/}/ fold'],
\	'separately': {
\		'*': {},
\		'tex': {
\			'parentheses': ['start=/(/ end=/)/', 'start=/\[/ end=/\]/'],
\		},
\		'lisp': {
\			'guifgs': ['royalblue3', 'darkorange3', 'seagreen3', 'firebrick', 'darkorchid3'],
\		},
\		'vim': {
\			'parentheses': ['start=/(/ end=/)/', 'start=/\[/ end=/\]/', 'start=/{/ end=/}/ fold', 'start=/(/ end=/)/ containedin=vimFuncBody', 'start=/\[/ end=/\]/ containedin=vimFuncBody', 'start=/{/ end=/}/ fold containedin=vimFuncBody'],
\		},
\		'html': {
\			'parentheses': ['start=/\v\<((area|base|br|col|embed|hr|img|input|keygen|link|menuitem|meta|param|source|track|wbr)[ >])@!\z([-_:a-zA-Z0-9]+)(\s+[-_:a-zA-Z0-9]+(\=("[^"]*"|'."'".'[^'."'".']*'."'".'|[^ '."'".'"><=`]*))?)*\>/ end=#</\z1># fold'],
\		},
\		'css': 0,
\	}
\}
" let g:jscomplete_use = ['dom', 'moz', 'es6th']
" autocmd FileType javascript :setl omnifunc=jscomplete#CompleteJS
augroup plugin-devdocs
	autocmd!
	autocmd FileType c,cpp,rust,haskell,python,javascript,jsx nmap <buffer>K <Plug>(devdocs-under-cursor)
augroup END

" ===== 表示 =====================================
" ----- 不可視文字の設定 -------------------------
set list
set listchars=tab:>-,eol:⏎,extends:»,precedes:«,nbsp:%,trail:@

" ----- color scheme -----------------------------
colorscheme desert
colorscheme hybrid " あればこっちを優先(これだけだとCUIの色が変わらない)

" ----- 色の設定 (ターミナル) --------------------
if !exists("g:terminal_ansi_colors")
	let g:terminal_ansi_colors = [
	  \ "#0c0c0c", "#c50f1f", "#13a10e", "#c19c00",
	  \ "#5555ff", "#881798", "#3a96dd", "#cccccc",
	  \ "#767676", "#e74856", "#16c60c", "#eadf84",
	  \ "#3b78ff", "#b4009e", "#61d6d6", "#e8e8e8"
	  \ ]
endif

" ----- 色の宣言(上書き) -------------------------
hi StatusLine guibg=#4242ff guifg=white gui=bold ctermfg=darkblue ctermbg=white cterm=reverse,bold
hi Title guibg=lightblue guifg=white ctermbg=lightblue ctermfg=white gui=bold
hi Comment ctermfg=darkgreen guifg=lightgreen
hi Statement guifg=lightyellow
hi Type ctermfg=blue guifg=lightcyan
hi Label ctermbg=darkyellow ctermfg=white guifg=#eeee55 guibg=#333300
hi Pmenu ctermbg=darkgray ctermfg=white guibg=darkgray guifg=white
hi PmenuSel ctermbg=lightblue ctermfg=white guibg=lightblue guifg=white
hi PmenuSbar ctermbg=darkgray ctermfg=lightgray guibg=darkgray guifg=lightgray
hi PmenuThumb ctermbg=darkgray ctermfg=lightgray guibg=darkgray guifg=lightgray
hi TabLine ctermbg=lightcyan ctermfg=black gui=bold term=bold
hi TabLineFill ctermbg=darkgray ctermfg=black gui=underline
hi TabLineSel ctermbg=blue ctermfg=white
hi Search ctermbg=red ctermfg=black
hi LineNr guifg=#555555
hi DiffDelete ctermbg=DarkMagenta ctermfg=white
hi Folded gui=bold term=standout guibg=grey30 guifg=black ctermbg=darkgray ctermfg=lightcyan
hi Visual ctermbg=blue ctermfg=black term=reverse
hi jediFunction ctermbg=darkblue ctermfg=white
hi SpecialKey ctermfg=darkgray

" ----- 色の宣言(オリジナル) ---------------------
hi Label ctermfg=black ctermbg=darkyellow
hi Label2 guifg=#e0b611 ctermfg=yellow
hi Label3 guifg=#b08d33 ctermfg=darkyellow
hi Bold gui=bold
hi Italic gui=italic
hi Striken guifg=#dddddd ctermfg=gray
hi HR guifg=gray ctermfg=darkgray
hi SuperHR guifg=lightgray guibg=darkcyan gui=italic ctermfg=lightgray ctermbg=blue
hi Citation guibg=#222200 guifg=lightyellow ctermbg=darkyellow ctermfg=black
hi TabCloseBox ctermbg=darkred ctermfg=white
hi RO ctermbg=red ctermfg=white guifg=white guibg=magenta
hi SpaceEnd ctermbg=red ctermfg=white guifg=white guibg=magenta
hi ZenkakuSpace ctermbg=darkgray guibg=#333333

" ----- 文法定義(見出し) -------------------------
au Syntax * syntax match Label display "^\* .*"
au Syntax * syntax match Label2 display "\t\* .*"
au Syntax * syntax match Label3 display "\t\t\* .*"
au Syntax * syntax match Label2 display "^[\t 　]*[・□■○●][^・].*"
au Syntax * syntax match Label display "^[・□■○●][^・].*"
au Syntax * syntax match Label2 display "^[\t 　]*\*\* .*"
au Syntax * syntax match Label3 display "^[\t 　]*\*\*\* .*"
au Syntax * syntax match Label display "^【.*】"
" au Syntax * syntax match HR display ".*-----.*"
au Syntax * syntax match SuperHR display ".*=====.*"

" ----- 文法定義(ハイライト) ---------------------
match Bold /\*\*.*\*\*/
match Italic /__.*__/
syntax region Citation start=".*>>>" end="<<<"
match ZenkakuSpace /　/
" テスト用 **abc** __def__ 　　 a     
"	 >>> This is citation <<<		
" ----- イタリック -------------------------------
set t_ZH=[3m
set t_ZR=[23m


" ===== スペルチェック============================
set spellfile=~/dotfiles/vimspell_en.utf-8.add 

" ===== 以下、関数 ===============================
" ----- タブライン -------------------------------
function! MyTabLine()
	let s = ''
	let tabname=''
	for i in range(tabpagenr('$'))
		let tabname=(i+1) . ':' . bufname(tabpagebuflist(i+1)[tabpagewinnr(i+1) -1])
		let tabname=substitute(tabname, $HOME, "~", 1)
		let tabname=substitute(tabname, $VIMRUNTIME, "(vim)", 1)
		let s .= '%' . (i + 1) . 'T'	"マウスクリック用
		if i + 1 == tabpagenr()
			let s .= '%#TabLineSel#/ ' . tabname . ' %#TabCloseBox#%999X[X]%X%#TabLineSel# \'
		else
			let s .= '%#TabLine#/ ' . tabname . ' %' . (i+1) . 'X[X]%X \'
		endif
	endfor
	let s .= '%#TabLineFill#%T%=Vi IMproved ver.'
	let s .=  version / 100 . '.' .	strpart(version, strlen(version)-2, 2)
	return s
endfunction

function! PreviewTeX()
	cd %:h
	exec "!platex --shell-escape-commands=extractbb '" . expand("%:p") . "'"
	exec "silent !dvipdfmx '" . expand("%:p:r") . ".dvi'"
	exec "silent !rm '" . expand("%:p:r") . ".dvi'"
	exec "silent !rm '" . expand("%:p:r") . ".log'"
	exec "silent !rm '" . expand("%:p:r") . ".aux'"
	exec "silent !mv '" . expand("%:p:r") . ".pdf' ~/tmp/"
	exec "silent !open \"" . expand("$HOME") . "/tmp/" . expand("%:r") . ".pdf\""
endfunction
command! PreviewTeX :<line1>,<line2>call PreviewTeX()

function! CharCount() range
	let l:count = a:firstline
	let l:linestr = ""
	
	let l:linecount = 0
	let l:halfwidth = 0
	let l:fullwidth = 0

	while l:count <= a:lastline
		let l:linestr = getline(l:count)
		let l:linecount += 1
		let l:strchars = strchars(l:linestr)	" あ = a = 1
		let l:strwidth = strwidth(l:linestr)	" あ = 2, a = 1
		let l:fullwidth += (l:strwidth - l:strchars)
		let l:halfwidth += (l:strchars * 2 - l:strwidth)

		let l:count += 1
		" echo l:count . ": (" . l:fullwidth . ", " . l:halfwidth . ") " .  l:linestr 
	endwhile

	let l:msg  = "** 文字数カウント **\n"
	let l:msg .= "  行数: " . l:linecount . "\n"
	let l:msg .= "  文字数: " . (l:halfwidth + l:fullwidth) . "\n"
	let l:msg .= "  文字数(全角を2文字と換算): " . (l:halfwidth + l:fullwidth * 2) . "\n"
	let l:msg .= "  文字数(全角を1文字と換算): " . printf("%g", l:halfwidth / 2.0 + l:fullwidth) . "\n"
	let l:msg .= "  半角: " . l:halfwidth . "\n"
	let l:msg .= "  全角: " . l:fullwidth . "\n"

	echo l:msg
endfunction
command! -range=% CharCount :<line1>,<line2>call CharCount()
