#include <iostream>
#include <vector>
#include <boost/range/irange.hpp>

using namespace std;

using namespace std::string_literals;

int main(int argc, char** argv){


	// if
	int a = 10;
	if (a < 10){
		cout << "less than 10" << endl;
	}else if (a == 10){
		cout << "equal to 10" << endl;
	}else{
		// 何もしないときは何も入れなくて良い
	}

	// ブロックを使用せずに単文を使用することも出来る。
	if (a == 10)
		cout << "a is 10!" << endl;

	// 初期化節をおくことも可能 [[C++17]]
	if (auto l = "abc"s.length(); l == 3)
		cout << "length is 3!" << endl;

	auto constexpr iec559 = numeric_limits<double>::is_iec559;
	if constexpr (iec559) {	// コンパイル時条件分け [[C++17]]
		cout << "IEC 559" << endl;
	}

	// for (初期化文; 条件; 繰り返し文)
	// 初期化節で宣言した変数はfor内のみで有効
	for (int i = 0; i < 5; i++){
		printf("%d\n", i);	// 0 1 2 3 4
	}

	// break, continue
	for (int i = 0; i < 5; i++){
		if (i == 4){
			continue;
		}else if(i == 5){
			break;
		}
	}

	// infinite loop
	for(;;){
		break;
	}
	
	for(int i = 0; i < 5; i++){
		// int i = 1;	// C++ではコンパイルエラー [[C/C++]]
		printf("%d\n", i);
	}

	// foreach (Range-based for) [[C++11]]
	vector<int> v = {1, 2, 3};
	for (const int i: v)	// constの値渡し
		cout << i << endl;
	for (int& i: v)	{		// リファレンス (auto&でも良い)
		i *= 2;				// constでなければ書き換えも可能
		cout << i << endl;
	}
	vector<bool> v2 = {true, false};
	for (auto&& b: v2)		// 右辺値参照 (vector<bool>のアイテムはリファレンスを取れない)
		cout << b << endl;
	
    for (auto i : boost::irange(0, 5)){ //  [[boost]]
        cout << i << endl;
    }

	// loop
	while (a > 0){
		a--;
	}

	while (a < 10){
		a++;
		if (a == 4) continue;
		if (a == 6) break;
	}

	do {
		a--;
	} while (a < 0);

	// switch (select case)
	switch(int len = "abc"s.length(); len){	// 整数, enumのみ可
		case 0:
			cout << "zero" << endl;
			break;
		case 3:
			cout << "three" << endl;	 // break忘れるとfallthrough[[注意]]
			[[fallthrough]];		// コンパイラにfallthroughを明示的に知らせる[[C++17]]
		default:
			cout << "other" << endl;
	}

// goto
	goto mylabel;
mylabel:
	return 0;

}

// g++ helloworld.cpp -o helloworld(実行ファイル名)
// clang++ helloworld.cpp -o helloworld
//	--std=c++11フラグなどでC++のバージョンを指定できる
