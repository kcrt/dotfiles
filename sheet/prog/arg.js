"use strict";

// [[Node.js]]
// process.argvでアクセス可能
// (process.argv[0] はnode, [1]がjsファイル)
for (let arg of process.argv){
	console.log(`${arg}`);
}

// コマンドライン引数を解釈する便利な方法はない


// node helloworld.js で実行
