#include <iostream>
#include <sstream>
#include <string>

using namespace std::string_literals;

int main(int argc, char** argv){

	std::cout << "Hello, world!" << std::endl;
	std::cout << stoi(std::string("123")) << std::endl;
	std::cout << stoi(std::string("0x123")) << std::endl;
	std::cout << stoi(std::string("0x2b"),nullptr,16) << std::endl;
	std::cout << stoi(std::string("2b"),nullptr,16) << std::endl;
	std::cout << stoi(std::string("1011"),nullptr,2) << std::endl;
	std::cout << stod(std::string("2.3")) << std::endl;
	std::cout << stod(std::string("0x1.ep6"s)) << std::endl;
	
	std::cout << static_cast<int>(true) << std::endl;
	std::cout << static_cast<bool>(1) << std::endl;
	
	std::stringstream ss;
	std::cout << "----" << std::endl;
	ss << std::hex << 123 << std::hexfloat << 12.3 << std::endl;
	std::cout << ss.str() << std::endl;
	std::cout << static_cast<int>(1.2) << std::endl;
	std::cout << static_cast<double>(1) << std::endl;
	std::cout << static_cast<long>(1) << std::endl;
	return 0;

}

// g++ helloworld.cpp -o helloworld(実行ファイル名)
// clang++ helloworld.cpp -o helloworld
//	--std=c++11フラグなどでC++のバージョンを指定できる
