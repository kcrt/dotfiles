#include <iostream>
#include <vector>
#include <limits>
#include <string>
using namespace std::string_literals;


#define CHECK(expr)		printf("%s is %s\n", #expr, (expr) ? "true" : "false")

int main(int argc, char** argv){

	int arr[] = {};
	std::vector<int> arr2;

	CHECK(0);
	CHECK(1);
	CHECK(0.0);
	CHECK(1.0);
	CHECK(std::numeric_limits<double>::quiet_NaN());
	CHECK(std::numeric_limits<double>::infinity());
	CHECK('0');
	CHECK('1');
	CHECK('A');
	//CHECK("0"s);
	//CHECK("1"s);
	//CHECK("A"s);
	//CHECK(""s);
	//CHECK("true"s);
	//CHECK("false"s);
	CHECK(arr);
	CHECK(sizeof arr);
	// CHECK(arr2);
	CHECK(nullptr);


	return 0;

}

// gcc helloworld.c -o helloworld(実行ファイル名)
// clang helloworld.c -o helloworld
