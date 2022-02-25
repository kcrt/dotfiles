#include <stdio.h>
#include <math.h>

#define CHECK(expr)		printf("%s is %s\n", #expr, (expr) ? "true" : "false")

int main(int argc, char** argv){

	int arr[] = {};

	CHECK(0);
	CHECK(1);
	CHECK(0.0);
	CHECK(1.0);
	CHECK(NAN);
	CHECK(+INFINITY);
	CHECK('0');
	CHECK('1');
	CHECK('A');
	CHECK('\0');
	CHECK("0");
	CHECK("1");
	CHECK("A");
	CHECK("");
	CHECK("true");
	CHECK("false");
	CHECK(arr);
	CHECK(NULL);


	return 0;

}

// gcc helloworld.c -o helloworld(実行ファイル名)
// clang helloworld.c -o helloworld
