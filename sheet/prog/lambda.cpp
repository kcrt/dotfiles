#include <iostream>

int main(int argc, char** argv){

	// [C++11]
	// [キャプチャ方法](引数リスト) -> 戻り値 { 関数 }
	// 但し、「-> 戻り値」は推論可能であれば省略できる。
	// 引数がない場合は「()」も省略できる。
	// キャプチャリスト: lambdaから見える変数を指定する
	// [x]: xをコピーして使用
	// [&x]: xを参照して使用
	// [&x, y]: xは参照、yはコピー
	// [&]: デフォルトで参照
	// [=]: デフォルトでコピー
	// [this]: メンバ関数・変数にアクセス可能に
	int a = 10;
	auto twice = [](int x) -> int {return x * 2;};
	auto twice2 = [](int x){return x * 2;};
	auto twice_a = [a]{return 2 * a;};

	std::cout << twice_a() << std::endl;
	return 0;

}

// g++ helloworld.cpp -o helloworld(実行ファイル名)
// clang++ helloworld.cpp -o helloworld
//	--std=c++11フラグなどでC++のバージョンを指定できる
