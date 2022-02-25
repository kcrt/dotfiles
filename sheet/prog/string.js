"use strict";

console.log("Hello, world");
console.log(`Hello, 
			world`);
console.log("Hello, \
			world");
console.log("Hello, " +
			"world");

var name="kcrt";
console.log(`My name is ${name}`);
console.log(name[0]);

console.log(String.raw`\a\b\c\"`)
console.log(typeof(/.*apple/))
console.log("abcde".substring(2,4))

// node helloworld.js で実行
