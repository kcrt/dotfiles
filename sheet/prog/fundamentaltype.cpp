#include <cstdio>
#include <limits>
#include <cmath>
#include <cinttypes>
#include <stddef.h>
#include <typeinfo>
#include <typeindex>	// C++11

#include <iostream>
using namespace std;

int main(int argc, char** argv){

// TODO: auto
// TODO: int a(3)やint a{3}などの書き方での初期化

	int x1 = 1, x2 = 2;

	/* 整数: char (最低8bit) , shortまたはshort int(最低16bit), int(最低16bit), long(最低32bit), long long(最低64bit [[C++11]]) */
	/* 符号付きのsignedと、符号なしのunsigned だが、省略すると符号付き (charのみ環境依存) */
	char c = 'a';					/* "文字列"ではなく、文字 'a' */
	signed int a = 32;				/* このsigned は省略可 */
	unsigned long long l = 1ULL;	/* 整数定数： 1U, 1L, 1UL, 1LL, 1ULL など (ullなど小文字も可) */

	cout << c << " and " << +c << endl;		/* a and 97; 単項+ で数値にする */
	cout << "size of 'a' is: " << sizeof('a') << endl;	/* 1, 'a'はchar [[diff_c_cpp]][[注意]] */

	/* 浮動小数点: float, double, long double, float_t[[C++11]], double_t[[C++11]] */
	double d = 24e-2;			/* なにもないとdouble; 3.14F (float), 3.14L (long double) */
	double d2 = 0x12.34P+10;	/* [[C++11]] 16進数で指定する */
	double d3 = std::nan("");	/* [[Cr+11]] <cmath> INFINITY, -INFINITY, NAN, std::isinf, std::isfinite, std::isnan, std::isnormalも使用可能 */
	/* NaNについてより詳しく知りたければquiet NaNとsignaling NaNを参照。 */
	double d4 = std::numeric_limits<double>::infinity(); /* <climits> 長い…。<cmath> INFINITYのほうが便利。 */

	cout << d << endl;
	cout << std::scientific << d << endl;

	/* 論理型 [[diff_c_cpp]] */
	/* C言語と違い、bool, true, falseは予約語である。*/
	bool b = 2;		/* trueになる */
	cout << b << endl;
	cout << std::boolalpha << b << endl;

	cout << b * 4 << endl;/* 4, 四則演算時にtrueは1(int)に自動で変換される */


	/* CやC++は変数の宣言だけでは初期化されない [[注意]] */
	int x;
	printf("unintialized value is: %d\n", x);	/* 何が出るか不明 */

	/* 定数 */
	const int aa = 3;

	/* wchar_t などchar以外の文字型に関してはunicode[[参照]] */

	/* 変数の上下限 */
	/* <climits> (limits.h)ももちろん使用可能だが<limits>の物を紹介する */
	cout << numeric_limits<long>::min() << " - " << numeric_limits<long>::max() << endl;
	numeric_limits<long>::min();
	/* min, max, epsilon, is_signed, is_integer, has_infinity, lowest[[C++11]] などを使用可能 */

	/* [[C++11]] <cstdtypes> */
	/* intN_t (N bitの整数) , int_leastN_t (最低N bitの整数), int_fastN_t (早いやつ) */
	/* 同様にuintN_t, uint_leastN_t, uint_fastN_t も使用可能 */
	/* N = 8, 16, 32, 64は最低でも使えることが保証されている。*/
	int64_t xxx = 1;

	/* ポインタ: intptr_t, 使える中で一番でかいやつ: intmax_t, uintmax_t */
	int64_t i64 = numeric_limits<int64_t>::min();
	cout << i64 << endl;

	/* char16_t, char32_t [[C++11]] についてはunicode[[参照]] */

	/* その他の型 */
	size_t t = sizeof(int);		/* サイズやループカウンタに使用 */
	ptrdiff_t pp = &d - &d2;	/* stddef.h: アドレスの差 */
	nullptr_t ppp = nullptr;		/* [[C++11]] */
	/* byte bb {1};				   [[C++17]] byte bb = 1 はエラー */

	cout << numeric_limits<double>::min() << endl;
	cout << numeric_limits<double>::max() << endl;
	cout << numeric_limits<double>::lowest() << endl;
	
	{
		int a = 1;
		decltype(a) b = 2;	// aと同じ型 
	}

	auto p = NULL;
	int xxxx = 1;
	cout << "type " << typeid(xxxx).name() << endl;
	cout << "type " << typeid(nullptr).name() << endl;
	cout << "type " << typeid(1).name() << endl;
	cout << "type " << typeid(1L).name() << endl;
	cout << "type " << typeid(1.1).name() << endl;
	cout << "type " << typeid("hello"s).name() << endl;
	cout << "type " << type_index(typeid("hello"s)).name() << endl;
// cout << nullptr << end;

	return 0;

}
