package main

import "fmt"
import "math/big"

func main() {

	a, ok := new(big.Int).SetString("12345678901234567890", 10) // 10進
	b := big.NewInt(5)
	a.Add(a, b) // a = a + b
	a.Exp(a, b, nil) // a = a ^ b (mod x)
	fmt.Println(a)

	// 制度設定
	x, _, err := big.ParseFloat("1.234567890123456", 10, 100, big.ToZero)	// 10進100bit
	y := big.NewFloat(10.5)
	x.Mul(x, y)		// x = x * y
	fmt.Println(x)

	println(ok)
	println(err)

}
