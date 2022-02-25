#!/bin/sh

showusage(){
	echo "ktAsk, Rev: 0.1"
	echo "指定した文を表示して、yまたはnを入力させます。"
	echo "  usage: $0 [-y|-n|-0] message"
	echo ""
	echo "引数："
	echo "    -y         (デフォルト)省略時はYとみなす(Y/n)"
	echo "    -n         省略時はNとみなす(y/N)"
	echo "    -0         省略を認めない(y/n)"
	echo "    message    表示するメッセージ"
	echo "返り値："
	echo "   0          Yが選ばれました"
	echo "   1          Nが選ばれました"
}


if [ $# == 0 ]; then
	showusage
	exit
elif [ $# == 1 ]; then
	asktype='-y'
	message=$1
elif [ $# == 2 ]; then
	case $1 in
		-y|-n|-0)
			asktype=$1
			message=$2;;
		*)
			showusage
			exit -1;;
	esac
else
	showusage
	exit -1
fi

while [ 1 ]; do
	echo -n $message;
	case $asktype in
		-y)
			echo -n " (Y/n):";;
		-n)
			echo -n " (y/N):";;
		-0)
			echo -n " (y/n):";;
	esac

	line=""
	read line

	if [ "$line" = "" ]; then
		if [ "$asktype" = '-y' ]; then line='y'; fi
		if [ "$asktype" = '-n' ]; then line='n'; fi
	fi
	
	
	case $line in
		y|Y)
			ans='y'
			exit 0;;
		n|N)
			ans='n'
			exit 1;;
	esac
done



