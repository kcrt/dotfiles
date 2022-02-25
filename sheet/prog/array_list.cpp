#include <iostream>
#include <vector>
#include <array>
#include <algorithm>
#include <functional>
#include <numeric>
#include <tuple>
#include <execution>

using namespace std;

int main(int argc, char** argv){

	// C言語と同じ通常の配列型も使用可能(説明省略)
	int carr[] = {1, 2, 3};		// 要素数は省略できる
	cout << carr[0] << endl;	// 要素へのアクセス
	cout << sizeof(carr) << endl; // 配列のサイズ(byte)
	cout << sizeof(carr) / sizeof(carr[0]) << endl; // 配列要素数

	// 可変長配列 (最も一般的)
	vector<int> arr{1, 2, 3};		// [[C++11]]
	vector<int> arr2a = {1, 2, 3};	// [[C++11]]
	vector<int> arr2b({1, 2, 3});	// [[C++11]]
	vector<int> arr2c(4, 10);		// 10, 10, 10, 10 [[C++03]]から使用できる
	// initializer list: {...}で、std::initializer_list<T>を生成して、通常の配列以外も初期化できるようになったのは[[C++11]]から
	// 固定長配列 [[C++11]]
	array<int, 3> arr3 {1, 2, 3};
	array<int, 3> arr3a = {1, 2, 3};

	// その他にもlist, dequeなど様々なSTLコンテナを使用することが出来る。

	cout << arr[0] << endl;	// 要素へのアクセス
	cout << arr.at(0) << endl;	// atでもok out_of_rangeあり
	cout << arr.front() << arr.back() << endl;	// 最初と最後
	int *pArr = arr.data();	// 生の配列型
	decltype(arr)::value_type x = arr[0];	// 要素の型 decltypeは[[C++11]]


	// 走査：iteratorはautoでもOK
	cout << "run" << endl;
	for(vector<int>::iterator it = arr.begin();
			it != arr.end();
			it++){
		cout << *it << endl;	// *でiteratorから値を取得
	}
	
	// イテレータ・リバースイテレータ (とそのconst版)
	arr3.begin(), arr3.end(), arr3.rbegin(), arr3.rend();
	arr3.cbegin(), arr3.cend(), arr3.crbegin(), arr3.crend();

	for(auto& i : arr){		// range based for
		cout << i << endl;
	}


	// 要素数
	cout << arr.size() << endl;

	auto is_odd = [](int& x){ return x % 2; };	// [[C++11]]
	
    // 要素のコピー
    auto new_arr = arr;
	cout << arr[0] <<endl;
	new_arr[0] = 999;
	cout << new_arr[0] <<endl;
	cout << arr[0] <<endl;

	// 検索
	count(arr.begin(), arr.end(), 2);	// 2の数を検索
	cout << "odd" << count_if(arr.begin(), arr.end(), is_odd) << endl;

	auto it1 = find(arr.begin(), arr.end(), 2);
	auto it2 = find_if(arr.begin(), arr.end(), is_odd);
	auto it3 = find_if(std::execution::par, arr.begin(), arr.end(), is_odd);
	cout << *it2 << endl;
	cout << *it3 << endl;
	// 見付からなければ第2引数を返す。

	// 存在確認
	any_of(arr.begin(), arr.end(), is_odd);
	// findを使用しても良い

	// 要素の追加・削除
	arr.push_back(4);
	arr.pop_back();
	cout << "ins" << endl;
	arr.insert(arr.begin() + 1, 10);

	for(auto& i : arr){
		cout << i << endl;
	}
	cout << "erase 2 " << endl;
	arr.erase(arr.begin() + 2);
	for(auto& i : arr){
		cout << i << endl;
	}
	arr.clear();

	arr = {1, 5, 4, 2, 8};

	// ソート
	sort(arr.begin(), arr.end());

	// 逆順
	reverse(arr.begin(), arr.end());
	// またはリバースイテレータを使用すれば良い
	arr.rbegin(), arr.rend();


	// function apply
	auto twotimes1 = [](int& x){ x *= 2; };	// [[C++11]]
	auto twotimes2 = [](int& x){ return x * 2; };	// [[C++11]]
	cout << "transform" << endl;
	for(auto& i : arr){
		cout << i << endl;
	}
	for_each(arr.begin(), arr.end(), twotimes1);
	for(auto& i : arr){
		cout << i << endl;
	}
	// for_each: 関数を適応
	// transform: 第3引数は出力先、返値を使用
	transform(arr.begin(), arr.end(), arr.begin(), twotimes2);
	for(auto& i : arr){
		cout << i << endl;
	}

	// filter
	vector<int> newarr;
	copy_if(arr.begin(), arr.end(), newarr.begin(), is_odd);

	arr = {1, 2, 3, 4, 5};


	// reduce (include <numeric>)
	// 処理を省略すると和の計算(operator +)となる。
	int prod = accumulate(arr.cbegin(), arr.cend(), 1, multiplies<int>());
	int prod2 = reduce(arr.cbegin(), arr.cend(), 1, multiplies<int>()); // accumulateとちがい、前からとは限らない[[C++17]]
	cout << prod << prod2 <<endl;
	// multipries以外にも、plus, minus, divides, modulus, equal_toなど色々ある [[C++11]]

	// max, min
	auto it = max_element(arr.begin(), arr.end());
	cout << *it << endl;
	// min_element, maxmin_element (pairを返す)
	
	// all
	arr = {20, 30, 40};
	auto gt10 =  [](const int &x){ return x > 10;};
	if (all_of(arr.cbegin(), arr.cend(), gt10))
		cout << "> 10" << endl;
	// any
	if (any_of(arr.cbegin(), arr.cend(), [](const int &x){ return x == 20;}))
		cout << "there is 20" << endl;

	// Tuple [[C++11]]
	auto t = make_tuple(1, 3.14, "Hello");
	cout << get<0>(t) << endl;	// -> 1
	auto [n, d, s] = t; // [[C++17]]
	tie(n, d, s) = t;	// [[C++11]]
	cout << s << endl;
	// 2つのアイテムに特化したpairも存在する。
	auto p = make_pair(1, "Hello");
	cout << p.first << p.second << endl;

	
	return 0;

}

// g++ helloworld.cpp -o helloworld(実行ファイル名)
// clang++ helloworld.cpp -o helloworld
//	--std=c++11フラグなどでC++のバージョンを指定できる
