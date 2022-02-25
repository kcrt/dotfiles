
/*
 * 	FILENAME - FILEDESCRIPTION
 *		Programmed by kcrt <kcrt@kcrt.net>
 */

#include <iostream>
#include <array>
#include <string>
#include <algorithm>
#include <vector>
#include <deque>

using namespace std;

int main(int argc, char** argv){

	/* ===== array [[C++11]] ===== */
	array<int, 3> ar1 = {5, 1, 2};
	array<string, 2> ar2 = {"hello", "world"};

	ar1[0] = 4;						// 最初の要素に代入
	ar1[10000];						// 範囲外もエラーにならない[[BOMB]]
	try{
		ar1.at(10);					// at()だとout_of_range[[ERROR]]
	}catch(out_of_range e){
		;
	}
	cout << ar1.size() << endl;		// => 3
	sort(ar1.begin(), ar1.end());	// 
	for(auto& a: ar1){
		a *= 10;					// 参照で受けると操作も可能
	}
	// for_eachも使用できる
	for_each(ar1.begin(), ar1.end(), [](int &x){x *= 2;});
	for(const int a: ar1){			// 値の取得
		cout << a << endl;
	}

	/* ===== vector ===== */
	vector<int> v1 = {1, 2, 3};
	v1.push_back(4);				// 末尾に追加
	v1.insert(v1.begin() + 2, 10);	// 途中に挿入
	v1[0] = 1;
	try{
		v1.at(10) = 1000;				// out_of_range[[ERROR]]
	}catch(out_of_range e){
		;
	}
	for(const int a: v1){
		cout << a << endl;
	}

	/* ===== deque ===== */
	deque<int> d1 = {1, 2, 3};
	d1.push_front(4);
	d1.push_back(5);
	d1.pop_front();					// 出し入れ自由
	cout << d1[2] << endl;			// 添字アクセス


// TODO: algorithm
// sort, advanceなど
	return 0;
}


