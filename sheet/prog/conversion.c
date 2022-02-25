#include <stdio.h>
#include <stdlib.h>
#include <math.h>

int main(int argc, char** argv){

	printf("%d\n", atoi("12"));
	printf("%e\n", atof("123.5"));

	printf("%ld\n", strtol("7b", NULL, 16));
	printf("%ld\n", strtol("1011", NULL, 2));
	printf("%e\n", strtod("0x1.eep6", NULL));

	char buf[256];
	snprintf(buf, sizeof buf, "%d", 123);
	printf("%s\n", buf);
	snprintf(buf, sizeof buf, "%e", 123.5);
	printf("%s\n", buf);
	
	printf("----\n");
	printf("%e\n", rint(12.6));
	printf("%e\n", trunc(1.6));
	printf("%d\n", (int)12.5);

	printf("Hello, world!\n");
	return 0;

}

// gcc helloworld.c -o helloworld(実行ファイル名)
// clang helloworld.c -o helloworld
