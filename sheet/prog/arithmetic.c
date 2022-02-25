#include <stdio.h>
#include <math.h>
#include <iso646.h>

int main(int argc, char** argv){

	double x = 1.0 / 2;

	printf("%d\n", 4 % 3);

	printf("%lf\n", fmod(-4, 3));
	printf("%lf\n", remainder(-4, 3));

	printf("%lf\n", fmod(4, 2.1));
	printf("%lf\n", remainder(4, 2.1));

	printf("%lf\n", sqrt(3UL));

	printf("1 / 0 is : %d\n", 1 / 0);
	printf("1.0 / 0 is : %lf\n", 1.0 / 0);

	printf(signbit(+0.0) ? "negative\n" : "positive\n");
	printf(signbit(-0.0) ? "negative\n" : "positive\n");

	printf("%d\n", not (1 == 1));
	return 0;

}

// gcc helloworld.c -o helloworld(実行ファイル名)
// clang helloworld.c -o helloworld
