package main

import ("fmt"; "time")

func main() {

	// == 型 ==
	// time.Time型を使用する

	// == 現在の日付と時刻 ==
	nowvar := time.Now();

	// == 指定の日付でオブジェクトを生成 ==
	bday := time.Date(1984, time.September, 24, 12, 3, 24, 0, time.UTC)
	// year, month(1-12), day, hour, min., second, nanosec, location
	// time.Septemberはもちろん9でもOK
	bday2, err := time.Parse(time.RFC3339, "1984-09-24T12:03:24+09:00")
	// 形式
	// ANSIC       = "Mon Jan _2 15:04:05 2006"
	// UnixDate    = "Mon Jan _2 15:04:05 MST 2006"
	// RubyDate    = "Mon Jan 02 15:04:05 -0700 2006"
	// RFC822      = "02 Jan 06 15:04 MST"
	// RFC822Z     = "02 Jan 06 15:04 -0700"
	// RFC850      = "Monday, 02-Jan-06 15:04:05 MST"
	// RFC1123     = "Mon, 02 Jan 2006 15:04:05 MST"
	// RFC1123Z    = "Mon, 02 Jan 2006 15:04:05 -0700"
	// RFC3339     = "2006-01-02T15:04:05Z07:00"
	// RFC3339Nano = "2006-01-02T15:04:05.999999999Z07:00"
	// 等
	fmt.Println(bday2)
	fmt.Println(err)

	// == オブジェクトからの取得 ==
	fmt.Println(bday.Year(), bday.Month(), bday.Day())
	// Hour(), Minute(), Seconds(), Nanoseconds()
	// YearDay()

	// == 曜日==
	fmt.Println(bday.Weekday())	// Weekday型: Sun = 0, Mon = 1, ... , Sat = 6 

	// == Unix time ==
	fmt.Println(bday.Unix()) // => Unix秒へ
	fmt.Println(bday.UnixNano()) // => Unixナノ秒へ
	day_from_epoch := bday.Unix()
	nanosec := int64(123)
	fmt.Println(time.Unix(day_from_epoch, nanosec))

	// == プロセッサー時間 ==
	// time.Now()で取得された時間は現在時とモノトニックの両方の性質を持つ。
	// すなわち、time.Now().Sub(start_time)
	// は、処理中に時刻の設定が変更になっても正確な経過時間が取得できる。
	fmt.Println(time.Now().Sub(nowvar))	// サンプル

	

	fmt.Println(bday)
	fmt.Println(nowvar)


	// TODO: .Clock
}
