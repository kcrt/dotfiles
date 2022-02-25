package main

import "fmt"
import "strconv"
import "reflect"
import "math"

func main() {
	i, err := strconv.Atoi("12")
	fmt.Println(i)
	fmt.Println(err)
	i, err = strconv.Atoi("aa")
	fmt.Println(i)
	fmt.Println(err)

	fmt.Println(strconv.Itoa(12))

	f, _ := strconv.ParseFloat("123.5", 64)
	fmt.Println(f)

	i64, err := strconv.ParseInt("12", 16, 64)
	fmt.Println(i64)
	i64, err = strconv.ParseInt("0x12", 0, 64)
	fmt.Println(i64)
	i64, _ = strconv.ParseInt("1001", 2, 0)
	fmt.Println("X")
	fmt.Println(i64)

	fmt.Println(strconv.FormatBool(true))

	fmt.Println(strconv.FormatFloat(10000.2222, 'e', -1, 64))

	fmt.Println(strconv.FormatInt(123, 16))
	fmt.Println(strconv.FormatInt(123, 2))

	f = 123.5
	fmt.Println(int(f))
	i = 123
	fmt.Println(float64(i))
	fmt.Println(reflect.TypeOf(float64(i)))
	fmt.Println(reflect.TypeOf(123 * 1.0))
	fmt.Println(reflect.TypeOf(int(123) * 1.0))

	// fmt.Println(fmt.Sprintf("%A", f))
	fmt.Printf("%x\n", math.Float64bits(123.5))

	// fmt.Println(int(123.5)) // ERROR

	fmt.Println(int(true))
	fmt.Println(int(false))
}
