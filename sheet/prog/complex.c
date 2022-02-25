#include <stdio.h>
#include <complex.h>
#include <tgmath.h>

int main(int argc, char** argv){

	/* [[C99]] 複素数: float _Complex, double _Complex, long double _Complex */
	/* bool同様、complex.hを読み込むとfloat complex といった名前を使用できる。*/
    double complex z = 1 + 2 * I;	/* 1 + 2i */
	double complex z2 = pow(z, z); //z ^ z;
	printf("z * z = %f + %f i\n", creal(z2), cimag(z2));
	/* float, long double用にcrealf, creallがあるが、tgmain.hを読み込むとcrealはマクロになり適切なものが呼ばれる */
	/* carg (偏角), conj (複素共役), cproj(リーマン球面上の射影) */

	/* 虚数型: float _Imaginaryなど */
	/* double imaginary y = 2 * I; optionalなのでサポートされていないことが多い。使用しない方が無難 */

	/* 三角関数：csin, ccos, ctanを使用する。float, long double用にはcsinf, csinlなどが用意されている。 */
	/* tgmain.hを使用すると、単にsinで適切な物が選ばれます！ */
	double complex y = sin(z);
	/* cosh, acos, acosh, exp, log, sqrt, fabs も使用可能*/

	double complex x = sqrt(-1 + 0 * I);
	printf("%f\n", cimag(x));



	return 0;

}
