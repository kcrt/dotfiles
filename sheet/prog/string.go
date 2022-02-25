package main

import "fmt"
import "reflect"
import "strings"

func main() {
	fmt.Println(reflect.TypeOf('a'))
	fmt.Println(reflect.TypeOf("String"))
	fmt.Println(`\a\b\c\"`)
	fmt.Println(`Hello
world`)


	s := "Hello 日本"
	fmt.Println(reflect.TypeOf(s[0]))
	fmt.Println(reflect.TypeOf('a'))
	fmt.Println(reflect.TypeOf(s[0:5]))

	s = "こんにちわ"
	println(s[0:4])
	r := []rune(s)
	fmt.Println(r[0:4])
	s = string(r)
	fmt.Println(s)
	fmt.Println(len(s))
	fmt.Println(len([]rune(s)))

	fmt.Println("ab" + "cd")
	fmt.Println(strings.Join([]string{"a", "b", "c"}, ","))

	println(strings.Count("abc", "a"))
	println(strings.TrimRight("abc.\n\n", "\n"))
	println(strings.ToUpper("abc"))
	println(strings.Repeat("abc", 3))


}
