
# ----- パスの設定(これも本当はzshenvに書くべき)
# (N-/): 存在しないディレクトリは登録しない。
# typeset -U path					# 重複したパスを登録しない
# NODEBINPATH=`npm bin -g 2> /dev/null`
# path=(
#       /usr/local/bin(N-/)
#       /usr/local/sbin(N-/)
# 	  /bin(N-/)
#       /sbin(N-/)
#       $HOME/local/bin(N-/)
#       $HOME/bin(N-/)
#       /opt/local/bin(N-/)
#       /usr/bin(N-/)
#       /usr/sbin(N-/)
#       /usr/games(N-/)
#       /usr/texbin(N-/)
#       $NODEBINPATH)
# typeset -U sudo_path			# 重複したパスを登録しない。
# typeset -xT SUDO_PATH sudo_path # -x: export も一緒に行う。 -T: 変数を連動させる
# sudo_path=(/sbin(N-/)
#            /usr/sbin(N-/)
#            /usr/local/sbin(N-/)
#            /usr/pkg/sbin(N-/))
# fpath=(/usr/share/zsh/*/functions
#        ${fpath})
# 
