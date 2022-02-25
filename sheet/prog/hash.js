"use strict";

// ECMAScriptには、歴史的に連想配列の代わりとしてよく使用されてきたObjectと、新しく使用できるMap [[2015]]がある。
// Objectの方がよく使用されているが、今後のことを考えてMapの使用になれていくことをおすすめする。

let personobj = {
    name: "Kyohei, Takahashi",
    nickname: "kcrt",
    addr: "kcrt@kcrt.net",
    "age": 34   // keyに""は会ってもなくても良い
};
let personmap = new Map([
    ["name", "Kyohei, Takahashi"],
    ["nickname", "kcrt"],
    ["addr", "kcrt@kcrt.net"],
    ["age", 34]
]);
console.log(personobj);
console.log(personmap);

// 取得
console.log(personobj.nickname);     // どちらでも良いが
console.log(personobj["nickname"]);  // .が好まれる
console.log(personmap.get("nickname"));
const {addr, age, nokey="default"} = personobj //Destructruring Assignment [[2015]]


// 追加
personobj.birthday = "1984-09-24";
personmap.set("birthday", "1984-09-24");

// 削除
delete personobj.age;
personmap.delete("age");
console.log("after delete:", personobj);
console.log("after delete:", personmap);

// 要素数
console.log(Object.keys(personobj).length)
console.log(personmap.size);

// キー存在確認
console.log(personobj.nokey)    // keyがなければundefined
console.log("nokey" in personobj)
console.log("name" in personobj)

personmap.has("nokey")  // => T/F

// 結合
let obj1 = {a: 1, b: 2};
let obj2 = {a: 3, d: 4};
Object.assign(obj1, obj2)   // obj1 += obj2
let newobj = Object.assign({}, obj1, obj2)   // newobj = obj1 + obj2
console.log("assign: ", newobj)
console.log("assign: ", obj1)

let map1 = new Map([["a", 1], ["b", 2]]);
let map2 = new Map([["a", 3], ["d", 4]]);
let newmap = new Map([...map1, ...map2]);
console.log(newmap);

// 走査
for (let [key, value] of Object.entries(personobj))
    console.log(`${key} is ${value}`);
for (let key of Object.keys(personobj))
    console.log(`${key} is ${personobj[key]}`);
for (let value of Object.values(personobj))
    console.log(`${value}`);
Object.entries(personobj).forEach(([key, value]) => {  //[[2015]]
    console.log(`${key} is ${value}`);
});

for (let [key, value] of personmap)
    console.log(`${key} is ${value}`);
// .keys(), .values()による走査は可能
personmap.forEach((value, key) => { // 順番[[注意]]
    console.log(`${key} is=> ${value}`);
});




// node helloworld.js で実行
