"use strict";

let a = 10;
let fruits = ["apple", "banana", "fig"];

console.log("a"); console.log("b");

if (a < 10){
	console.log("less than 10.");
}else if(a == 10){
	console.log("equal to 10.");
}else{

}


// for
for (let i = 0; i < 5; i++){
	console.log(i);
}

// break and continue
OuterLoop: for (let i = 0; i < 5; i++){
	InnerLoop: for (let j = 0; j < 5; j++){
		if (j == 2){
			continue;
		}else if (j == 3){
			continue OuterLoop;
		}else if (j == 4){
			break;
		}
	}
}


// foreach
// for in:
//	オブジェクトの列挙可能(Enumerable)なプロパティを取得する。
//	予期せぬプロパティ(プロトタイプのものも含む)を取得してしまう可能性がある。
// for of [[2015]]:
//	Iterableなオブジェクト(配列を含む)から値を取得する。
for (let i in fruits){
	console.log(i)	// 0, 1, 2
	console.log(fruits[i])	// apple, banana, fig
}
for (let fruit of fruits){
	console.log(fruit)	// 
}
// map, forEachに関しても参照 TODO:

// while
while(a > 0){
	a--;
}
do{
	a++;
}while(a < 5);

// infinite loop
for (;;){
	break;
}
// switch
// 整数でなくても良い
switch(a){
	case 0:
	case 1:
		console.log("0 or 1");
		break;
	case 2:
		console.log("two");	// fallthrough
	default:
		console.log("other");
}

// goto
// ない

// node helloworld.js で実行
