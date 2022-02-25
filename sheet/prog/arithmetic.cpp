#include <iostream>
#include <cmath>
#include <functional>
using namespace std;

int main(int argc, char** argv){

	std::cout << 1 / 2 << std::endl;
	std::cout << 1.0 / 2 << std::endl;
	std::cout << 10 / 3 << std::endl;
	std::cout << 10 % 3 << std::endl;
	std::cout << fmod(4, 2.1) << std::endl;
	std::cout << remainder(4, 2.1) << std::endl;

	std::cout << abs(4L) << std::endl;
	std::cout << abs(4.1) << std::endl;

	std::cout << (32 >> 2) << std::endl;
	std::cout << (-32 >> 2) << std::endl;
	
	std::cout << (7 & 5) << std::endl;
	std::cout << (7 bitand 5) << std::endl;
	std::cout << (true && false) << std::endl;
	std::cout << (not false) << std::endl;

	auto a = 3;
	a and_eq 2;

	std::cout << std::plus<int>()(2, 3) << std::endl;
	return 0;

}

// g++ helloworld.cpp -o helloworld(実行ファイル名)
// clang++ helloworld.cpp -o helloworld
//	--std=c++11フラグなどでC++のバージョンを指定できる
