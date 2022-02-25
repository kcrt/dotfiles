package main

import (
	"flag"
	"fmt"
	"os"
)

func main() {

	// os.Argsでアクセス可能
	// (os.Args[0]は実行ファイル)
	fmt.Println(os.Args)

	// 引数解釈にはflagパッケージを使用する
	var (
		n = flag.Int("n", 100, "Number of apple(s)")
		filename = flag.String("filename", "default", "Target filename")
		sw = flag.Bool("sw", false, "Switch")
			// していなければfalse, あればtrue
	)
	flag.Parse()
	// --helpも自動的に実装される

	fmt.Println("There are", *n, "apples.")
	fmt.Println("Going to process", *filename)
	fmt.Println("Switch is:", *sw)


}
