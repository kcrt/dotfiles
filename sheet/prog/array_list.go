package main

import "fmt"
import "sort"
import "strconv"
import "reflect"

func main() {

	// 配列(固定長)とスライス(可変長)を使用できる。
	// スライスの方が便利なのでよく使用される。
	arr1 := [5]int{1, 2, 3, 4, 5}   // 配列
	arr2 := [...]int{1, 2, 3, 4, 5} // 配列 (要素数省略)
	fmt.Println(reflect.TypeOf(arr2))
	slice := []int{1, 2, 3, 4, 5} // スライス
	slice2 := make([]int, 5, 10)  // 型, 個数, 容量(=確保長, 省略可)
	var slice3 []int              // 要素のないスライス

	fmt.Println(slice[0])            // 0-origin
	fmt.Println(slice[len(slice)-1]) // 最後のアイテム
	slice[0] = 10                    // 要素への代入

	// 簡易スライス表現
	// Pythonでいうスライス(配列またはスライスから)
	fmt.Println(slice[1:3]) // slice[1], slice[2]
	fmt.Println(slice[2:])  // 2 - last
	fmt.Println(slice[:3])  // 0 - 2
	fmt.Println(slice[:])   // 0 - last

	// コピー
	s1 := slice[:] // Pythonと違ってこれはコピーではない！ [[注意]]
	s1[1] = 100    // もとのスライスも変更されてしまう (ただし、capacityを超えると別のデータになったり…)
	s2 := make([]int, len(slice))
	copy(s2, slice)                    // これでコピーとなる
	s3 := append([]int(nil), slice...) // これでもOK
	s2[1] = 123
	fmt.Printf("%v\n", s2)
	fmt.Printf("%v\n", s3)
	fmt.Printf("%v\n", slice)

	fmt.Println(len(slice)) // 要素長
	fmt.Println(cap(slice)) // 容量

	// 走査
	println("run")
	for i, val := range slice {
		fmt.Println(i, val) // i -> index, val -> item
	}

	// 一致の検索

	// 要素の追加
	slice = append(slice, 10, 11, 12)
	fmt.Printf("%v\n", append(slice, 11))
	fmt.Printf("%v\n", slice)

	slice = append(slice, slice2...) // ...が必要
	fmt.Printf("%v\n", slice)

	// appendは便利だが使用に注意が必要
	// 再代入を行わなければ、配列の内容は変わらないが
	// かといって、項目が追加された新しい配列を返しているわけではない…[[注意]]
	slicex := append(slice, 100)
	slicey := append(slice, 200)
	println("slicex")
	fmt.Println(slice)
	fmt.Println(slicex)
	fmt.Printf("%v\n", slicex)
	fmt.Printf("%v\n", slicey) // 同じ結果！[[注意]]

	// 先頭への要素の追加
	slice = append([]int{100}, slice...) // [[heavy]]
	fmt.Printf("%v\n", slice)

	// 要素の削除
	fmt.Printf("before: %v\n", slice)
	slice = append(slice[:2], slice[3:]...) // slice[2]抜き
	fmt.Printf("after del: %v\n", slice)
	// 末尾削除
	slice = slice[:len(slice)-1]
	// 先頭削除
	slice = slice[1:]

	// ソート
	// package sort
	fmt.Printf("before sort: %v\n", slice)
	sort.Ints(slice)
	// 他に、Float64s, Stringsもある
	fmt.Printf("after sort: %v\n", slice)
	sort.Stable(sort.IntSlice(slice)) // Stableなソート
	sort.Sort(sort.Reverse(sort.IntSlice(slice)))

	// 逆順
	// ない
	// See: Go SliceTricsk
	// https://github.com/golang/go/wiki/SliceTricks

	// map, foreach
	// ない…

	// filter
	// ない。自分で実装するしかない
	// (Go公式のSliceTricksより)
	fmt.Printf("before: %v\n", slice)
	n := 0
	for _, x := range slice {
		if x > 5 {
			slice[n] = x
			n++
		}
	}
	slice = slice[:n]
	fmt.Printf("filtered: %v\n", slice)

	// reduce
	// ない…

	// max min
	// ない…

	// all, any ない

	// interface{}を介せば型を混ぜることが出来る
	mixed := []interface{}{1, 3.14, "Hello"}

	// tupleではないが多値 (multiple-value)がある
	t1, t2 := 1, 2
	i, err := strconv.Atoi("12")
	fmt.Println(t1, t2)
	fmt.Println(i, err)

	println(arr1[0])
	println(arr2[0])
	println(slice[0])
	println(slice2)
	println(slice3)
	println(mixed[0])

}
