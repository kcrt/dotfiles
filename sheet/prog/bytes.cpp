#include <iostream>
#include <cstddef>

using namespace std;

int main(int argc, char** argv){

	// C++なのにcstddefで定義
	byte bb {0xDE};	// [[C++17]]
	cout << to_integer<int>(bb) << endl;
}

// g++ helloworld.cpp -o helloworld(実行ファイル名)
// clang++ helloworld.cpp -o helloworld
//	--std=c++11フラグなどでC++のバージョンを指定できる
