package main

import (
	"fmt"
	"math"
	"math/cmplx"
)

func main() {
	a := 3
	a = 5 - 5
	fmt.Printf("%.2f\n", math.Pi)
	fmt.Printf("%.2f\n", math.E)
	fmt.Printf("%.2f\n", math.Abs(-2))
	fmt.Println(math.Abs(-5))
	fmt.Println(math.Abs(-5.1))
	fmt.Println(math.Float32bits(1.3))
	fmt.Println(math.Ilogb(4))
	fmt.Println(math.Mod(10, 3))
	fmt.Println(math.Signbit(3))
	fmt.Println(math.Abs(float64(a)))
	fmt.Println(^-1)
	fmt.Println(15 &^ 2)
	fmt.Println(float64(a) / 0.0)
	fmt.Println(5 / float64(a))
	fmt.Println(math.Sqrt(-1))
	fmt.Println(cmplx.Sqrt(-1))

}
