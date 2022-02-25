"use strict";


let arr = [1, 2, 3, 4, 5];
arr[0];	// 最初の要素
arr[arr.length - 1];	//最後の要素
console.log(arr.slice(1, 3))	// スライスも使用できる。=>[2, 3]
console.log(Array())	// 空の配列
console.log([])			// 空の配列

let arr2 = arr;
arr2[0] = 100;			// Pythonと同じくコピーにはならない
console.log(arr);
arr2 = arr.slice()		// Pythonのarr[:]と同じ
arr2[0] = 200;			
console.log(arr);

console.log(Array(3, 4, 5))	// [3, 4, 5]
console.log(Array(3))		// 要素数3の配列 [[注意]]

console.log(arr.length)

// 一致の検索
arr.includes(100);	// t/f [[2016]]
arr.indexOf(100);	// 見付からなければ-1
arr.find(x => x > 10);		// あればその値, なければundefined [[2015]]
arr.findIndex(x => x > 10);		// あればindex, なければ-1 [[2015]]

// 要素の追加
arr.push(200);				// 末尾に追加
arr.push(201, 202);			// 複数追加
arr.push([203, 204]);		// これだと[203,204]を一つの要素として追加(Pythonのappend)
arr.pop()
arr.push(...[203, 204]);	// 203と204を追加(Spread構文) [[2015]]
console.log(arr)
// 先頭/任意の箇所への追加
arr.unshift(5);				// 先頭に追加
console.log(arr.shift())	// 先頭から取得して削除

// 削除
console.log(arr.pop())		// 最後の要素を取得して削除

arr2.length = 0				// 全削除
console.log(arr2)

// ソート
arr = [1, 2, 100, 3]
arr.sort();		// 配列をソートする
console.log(arr)	// => [1, 100, 2, 3] [[注意]]
// 標準は辞書順比較！
arr.sort((a, b) => a - b); // 数値として比較してソート
console.log(arr)		// [1, 2, 3, 100] [[OK]]

// 逆順
arr.reverse();
console.log(arr);

// map (function apply, foreach)
let arr3 = arr.map(x => x * x);		// 新しい配列を作る
arr.forEach(x => console.log(x));	// 要素に関数を適応する
arr.forEach((value, index, arr) => console.log(value));	// indexや配列そのものも取得できる。

// filter
let arr4 = arr.filter(x => x > 10);	// 10以上の要素のみ

// reduce
let prod = arr.reduce((x, y) => x * y);
console.log(prod);

// minmax
console.log(Math.min(...arr));		// Spreadを使用する

// all
arr = [20, 30, 30]
if(arr.every(x => x > 10))
	console.log("all > 10");
// any
if(arr.some(x => x == 20))
	console.log("There is 20");

// tuple



