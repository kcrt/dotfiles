"use strict";

console.log( 0 ? "true" : "0 is false");
console.log( 1 ? "1 is true" : "false");
console.log( 0.0 ? "true" : "0. is false");
console.log( 1.0 ? "1. is true" : "false");
console.log(NaN  ? "true" : "nan is false");
console.log(Infinity  ? "Inf is true" : "false");
console.log("0"  ? "str0 true" : "false");
console.log("1"  ? "str1 true" : "false");
console.log("A"  ? "strA true" : "false");
console.log(""  ? "true" : "nullstr false");
console.log("true"  ? "strtrue true" : "false");
console.log("false"  ? "strfalse true" : "false");
console.log([]  ? "emptyarr true" : "false");
console.log(undefined  ? "undef true" : "undef false");
console.log(null  ? "true" : "null false");

if(undefined){
	console.log("it's true")
}else{
	console.log("it's false")
}

// node helloworld.js で実行
