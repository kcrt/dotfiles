"use strict";

// lambdaのためにアロー関数がよく使用される


let twice = (x) => {return x * 2};

// 引数が1つの場合、()を省略できる。
// また、returnなしで直接式を書いても良い。
let twice2 = x => x * 2;


console.log(twice(10));
console.log(twice(20));
// node helloworld.js で実行
