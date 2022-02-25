package main

import "fmt"
import "math/cmplx"

func main() {
	c := 1 + 2i
	fmt.Println(c)
	fmt.Println(real(c))
	fmt.Println(imag(c))
	fmt.Println(complex(1, 2))
	fmt.Println(cmplx.Conj(c))
	fmt.Println(cmplx.Pow(c, c))
}
