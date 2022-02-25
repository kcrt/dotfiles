package main

import "fmt"
import "time"
import "reflect"
import "math"
import "strings"
import "unsafe"

func main() {

	var a int = 32
	var helloMessage = "Hello, world!" // 省略した型は推定される
	var x, y, z = 1, "Hello", 3.2      // 一度に複数もOK
	var b int                          // 数値を省略すると0や"など、型に合った値で初期化される
	d := 2
	fmt.Println(a, b, x, y, z, d)

	/* 整数: uint, int */

	/* 浮動小数点: float32 float64 */
	var f float64 = 24e-2
	math.Inf(1) /* Inf(正の数値) = +Inf, Inf(負の数値) = -Inf */
	math.NaN()  /* not a number */
	/* math.IsInf(), math.IsNaN() */
	println(math.MaxFloat64)				// DBL_MAXに相当
	println(math.SmallestNonzeroFloat64)	// DBL_MINに相当
	fmt.Println("----")
	fmt.Printf("%v\n", f)
	fmt.Printf("%f\n", f)
	fmt.Printf("%e\n", f)
	fmt.Println("----")

	/* 論理型 */
	var m bool = false /* true と false */

	/* 定数 */
	const aa = 32
	const (
		bb = 3
		cc = 4
	)

	/* runeなどに関してはstring, unicode[[参照]] */

	/* 変数の上限･下限 */
	// ERROR fmt.Println(math.MinInt)
	println(math.MinInt8)
	println(math.MaxUint8)
	// MaxInt8, MinInt8, MaxInt16, MinInt16, MaxInt32, MinInt32, MaxInt64, MinInt64, MaxUint8, MaxUint16, MaxUint32, MaxUint64

	p := uintptr(unsafe.Pointer(&a))

	/* サイズの決まっている型
	int8, int16, int32 == rune, int64
	uint, uint8 == byte, uint16, uint32, uint64 */
	var l int64 = 0x123456789abcdef0

	/* 型の確認 */
	fmt.Println(reflect.TypeOf(helloMessage))
	fmt.Println(reflect.TypeOf("a"))

	fmt.Println(f, m, l, p) // DELETE THIS

	/* Channel型 */
	// go routine間のデータのやりとり
	var ch_send chan<- int	// 送信専用
	var ch_recv <-chan int	// 受信専用
	var ch_both chan int	// 送受信用

	reflect.TypeOf(ch_send)
	reflect.TypeOf(ch_recv)
	reflect.TypeOf(ch_both)
	
	ch1 := make(chan string, 5)	// バッファサイズ5
	ch2 := make(chan string, 5)	// バッファサイズ5
	ch3 := make(chan string, 5)	// バッファサイズ5

	go func() {
		for {
			s := <-ch1			// ch1から受け取って…
			time.Sleep(1 * time.Second)	// 1秒待って…
			ch2 <- strings.ToUpper(s)	// 大文字にしてch2に渡す
			ch3 <- strings.ToLower(s)	// 小文字にしてch3に渡す
		}
	}()


	ch1 <- "Hello"
	ch1 <- "World"
	ch1 <- "END"

ChannelLoop:
	for {
		select {
			case v:= <-ch2:
				fmt.Println(v)
				if v == "END" { break ChannelLoop }
			case v:= <-ch3:
				fmt.Println(v)
			default:
				// do nothing
		}
	}

	close(ch1)
	close(ch2)

}
