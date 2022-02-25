#include <stdio.h>
#include <limits.h>
#include <float.h>
#include <math.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stddef.h>

int main(int argc, char** argv){


	int xxx1 = 1, xxx2 = 2;

	/* 整数: char (文字として%c、数値として%hhi, %hhu; 最低8bit) , shortまたはshort int (%hi, %hu; 最低16bit), int(%iまたは%d, %u; 最低16bit), long (%li, %lu; 最低32bit), long long (%lli, %llu; 最低64bit [[C99]]) */
	/* 符号付きのsignedと、符号なしのunsigned だが、省略すると符号付き (charのみ環境依存) */
	char c = 'a';					/* "文字列"ではなく、文字 'a' */
	signed int a = 32;				/* このsigned は省略可 */
	unsigned long long l = 1ULL;	/* 整数定数： 1U, 1L, 1UL, 1LL, 1ULL など (ullなど小文字も可) */

	printf("%c and %hhu\n", c, c);					/* a and 97 */
	printf("%d\n", (char)-1);					/* integer promotion */
	printf("size of 'a' is: %zu\n", sizeof('a'));	/* 4, 'a'はint [[diff_c_cpp]][[注意]] */

	/* 浮動小数点: float (%f, %e, %g, %a[[C99]]), double (%lf, ...), long double (%Lf, ...); float_t[[C99]], double_t[[C99]] (最低でもfloatまたはdoubleの幅を持つ型) */
	/* TODO: %fはdouble!!! default argument promotion (float to double) */
	double d = 24e-2;			/* 定数はなにもないとdouble; 3.14F (float), 3.14L (long double) */
	double d2 = 0x12.34P+10;	/* [[C99]] 16進数で指定する */
	double d3 = INFINITY;		/* [[C99]] <math.h> INFINITY, -INFINITY, NAN, isinf, isnanも使用可能。 [[C99]]以前では無限大はHUGE_VAL。 */
	printf("%f %e %g %a\n", d, d, d, d);	/* 0.240000 2.400000-e01 0.24 0x1.eb85(略)p-3 */

	/* [[C99]] 論理型 [[diff_c_cpp]] */
	/* 後方互換性のため論理型は_Boolという名前になっている。 */
	/* stdbool.hを読み込むとbool, true, falseという名前を使用できる。*/
	bool b = 2;
	printf("%d\n", b);	/* 2でなくて1 [[注意]] */
	unsigned long b1 = true + 4294967295U;	/* trueは単なる1、1週回ってb1は0になる*/
	b += 4294967294U;						/* boolなら1 (安全) */
	printf("boolean: %d\n", (int) b);
	printf("boolean: %d\n", (bool) !!99);

	/* CやC++は変数の宣言だけでは初期化されない [[注意]] */
	int x;
	printf("unintialized value is: %d\n", x);	/* 何が出るか不明 */

	/* 定数 */
	const int aa = 3;

	/* wchar_t などchar以外の文字型に関してはunicode[[参照]] */

	/* limits.h - 変数の上限・下限 */
	/* SCHAR_MIN, SHRT_MIN, INT_MIN, LONG_MIN, LLONG_MIN[[C99]] */
	/* SCHAR_MAX, SHRT_MAX, INT_MAX, LONG_MAX, LLONG_MAX[[C99]] */
	/* UCHAR_MAX, USHRT_MAX, UINT_MAX, ULONG_MAX, ULLONG_MAX[[C99]] */
	/* CHAR_MIN, CHAR_MAX */
	/* float.h - 変数の上限・下限 */
	/* FLT_MIN, DBL_MIN, LDBL_MIN and FLT_MAX, DBL_MAX, LDBL_MAX */
	/* FLT_EPSILON, DBL_EPSILON, LDBL_EPSILON */
	printf("long is %li - %li\n", LONG_MIN, LONG_MAX);
	printf("min, max = %e - %e\n", DBL_MIN, DBL_MAX);

	/* [[C99]] inttypes.h (または stdint.h) */
	/* intN_t (N bitの整数) , int_leastN_t (最低N bitの整数), int_fastN_t (早いやつ) */
	/* 同様にuintN_t, uint_leastN_t, uint_fastN_t も使用可能 */
	/* N = 8, 16, 32, 64は最低でも使えることが保証されている。*/
	/* ポインタ: intptr_t, 使える中で一番でかいやつ: intmax_t, uintmax_t */
	int64_t i64min = INT64_MIN;
	printf("%" PRId64 "\n", i64min);	/* PRI(d|u)N マクロを使用する */
	intptr_t ad = (intptr_t) &d;

	/* その他の型 */
	size_t t = sizeof(int);			/* サイズやループカウンタに使用 */
	ptrdiff_t pp = &d - &d2;		/* stddef.h: アドレスの差 */

	// TODO: +a (+によるshort -> int)
	return 0;

}
