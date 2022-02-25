package main

func main() {
	// Goでは関数リテラルと呼ばれる。
	twice := func(x int) int { return x * 2 }

	println(twice(2))
}
