#
#	065-functions_general.zsh
#		General utility functions
#

# ----- 関数
function _w3m(){
	W3MOPT=
	IsScreen=`expr $TERM : screen`
	if [[ $IsScreen != 0 ]]; then
		W3MOPT=-no-mouse
	fi
	set_title w3m $1
	if [[ $1 == "" ]]; then
		\w3m $W3MOPT http://www.google.co.jp
	else
		\w3m $W3MOPT $@
	fi
	set_title $SHELL
}
function testarchive(){
	if [[ ${1:e} = "zip" ]]; then
		zip -T $1
	elif [[ ${1:e} = "rar" ]]; then
		unrar t $1
	fi
}
function testallarchive(){
	for i in *.(zip|rar|lzh); do;
		testarchive $i
	done;
}
function backupnethack(){
	DATETIME=`date +"%Y%m%d_%H%M%S"`
	cp /usr/local/Cellar/nethacked/1.0/libexec/save/501kcrt.Z ~/backup/nethacked-backup-${DATETIME}-501kcrt.Z
}
function python_update() {
	if [[ -x conda ]]; then
		conda update conda
		conda update anaconda
		conda update --all
	fi
	pip install --upgrade pip
	pip freeze --local | grep -v '^\-e' | cut -d = -f 1 | xargs pip install --upgrade
}
