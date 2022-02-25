package main

import "fmt"
import "strconv"

func main() {
	a := 10
	fruits := []string{"apple", "banana", "fig"}

	// if
	if a < 10 {
		fmt.Println("less than 10.")
	} else if a == 10 {
		fmt.Println("equal to 10.")
	} else {

	}
	if i, _ := strconv.Atoi("2"); i == 2 {
		// 初期化節; 条件 も使用できる。
		fmt.Println("2")
	}

	// for
	for i := 0; i < 5; i++ {
		fmt.Println(i)
	}

	// for each (range clause)
	for i, f := range fruits {
		fmt.Println(i, f) // i -> index, f -> item
	}
	// range構文は適応するもので手に入るモノが違う
	// array/slice -> index, item
	// string -> index, rune
	// map -> key, value
	// channel -> element

	// break, continue
OuterLoop:
	for i := 0; i < 5; i++ {
	InnerLoop:
		for j := 0; j < 5; j++ {
			if j == 3 {
				continue
			} else if j == 4 {
				continue OuterLoop // ラベルを指定できる
			} else if j == 5 {
				break InnerLoop // breakも同様
			}
		}
	}

	// loop
	for a > 2 {
		a--
	}

	// infinite loop
	for {
		break
	}

	// Switch (初期化節も使用できる)
	// また、必ずしも整数でなくても良い (文字列でもOK)
	switch l := len("abc"); l {
		case 0, 1, 2, 3:
			// カンマで区切って値を指定できる。
			println("0-3")	// 標準でbreak不要！
		case 4:
			println("4")
			fallthrough		// fallthroutも指定可能
		default:
			println("other")
	}


	// interfaceのtype switch
	var iface interface {}
	iface = 3
	switch iface.(type) {
		case nil:
			println("nil")
		case int:
			println("int")
	}
	switch {
		case a == 0:
			println("zero")
		case a == 1:
			println("one")
			// if else チェーンの代わりにも使用できる。
	}

	


	goto MyLabel
MyLabel:
}
