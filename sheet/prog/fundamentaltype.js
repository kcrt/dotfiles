"use strict";

/* var, letの違いはスコープ */
{
	var a = 1;
	let b = 2;
	// c = 3;			// グローバル変数、strictモードではエラー！
}
console.log(a);			// 1
// [[ERROR]] console.log(b);		// スコープ外なのでエラー!

/* 数値 (Number) */
/* ECMAScriptには"整数型"はないが、丸めが行われているかは確認できる。 */
console.log(Number.isSafeInteger(1000000000000000));	// true: 丸められていない。
console.log(Number.isSafeInteger(10000000000000013));	// false: 2^53 - 1(Number.MAX_SAFE_INTEGER)以上はnot safe
console.log(Number.isInteger(10000000000000013));		// 整数ではある
console.log(10000000000000013);							// 10000000000000012となる [[注意]]
/* 配列では、Int8Arrayなどで整数を扱うことが出来る array [[参照]] */ 

let d = 3.2e-2;
let d2 = Infinity;		// Infinity, -Infinity, NaN(またはNumber.NaNを使用可能
let d3 = -0;			// 0と-0は一応区別される (が、0 === -0)
Number.isFinite(d2);	
Number.isNaN(d2)
isNaN(d2)				// 厳密には少し挙動が違う
NaN;
Number.NaN;
NaN === NaN				// false

a = 0.024
console.log(a.toFixed(5));
console.log(a.toPrecision(5));
console.log(a.toExponential());
console.log(a.toExponential(5));

/* 論理型(Boolean) */
true
false

/* 定数 */
const x = 32;
// [[ERROR]] x = 4;					// エラー！再代入出来ない
const arr = [1, 2, 3]
arr[2] = 4;					// 他の言語と違い、要素は変更できる [[注意]]

/* 変数の上限・下限 */
console.log(Number.MAX_VALUE);	// これ以上はInfinityになる。
// 他に、MIN_VALUE, EPSILON, MAX_SAFE_INTEGER, MIN_SAFE_INTEGER


/* 型の確認 */
console.log(typeof x);		// number

/* ECMAScript 固有の型 */
// Null型 と Undefined型
// nullはオブジェクトが存在しないことを示す。該当するオブジェクトがない場合などに使う。
// 例えば、document.getElementById("存在しないID")は、null。
// undefinedは値がまだ代入されていない変数などに使われる。
// nullはリテラルだが、undefinedはグローバル変数。
var xx;
console.log(xx);				// 何も代入されていないのでundefined
if(xx === undefined){
	// undefinedであるかは、===で確認。
}else if(xx == undefined){
	// ==だと、xxがnullでもtrueになる。
}else if(xx === void 0){
	// void演算子は、何を渡されてもundefinedを返す。
	// undefinedが再代入可能であった時代はvoid 0をundefinedの代わりに使用していた。
}
typeof null					// 本来ならnullとなるべきだがobject

// Symbol 型
var sym1 = Symbol("Hello");		// 引数は単なるデバッグ用の情報。
var sym2 = Symbol("Hello");
console.log(sym1 === sym2);		// false。Symbolは作るたびに別物になる。
console.log(Symbol.iterator);	// array [[参照]]


// TODO: empty, BigInt (将来のES)
