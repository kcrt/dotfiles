package main

import "fmt"

func main() {

	var person = map[string]string{ // string -> stringなmap
		"name":     "Kyohei, Takahashi",
		"nickname": "kcrt",
		"addr":     "kcrt@kcrt.net",
		"age":      "34", // 「,」か「}」が必要
	}
	fmt.Println(person)

	// 内容の参照
	println(person["name"]) // 存在しなければ型の初期値

	// 辞書追加・変更
	person["birthday"] = "1984-09-24"
	// 削除
	delete(person, "age")
	// 項目数
	println(len(person))
	// キーの存在確認
	if val, ok := person["name"]; ok {
		println(val)
	} else {
		println("no key")
	}
	// 結合
	// ない
	// 走査
	for key, value := range person {
		fmt.Println(key, "is", value)
	}

}
