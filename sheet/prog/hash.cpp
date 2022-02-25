#include <iostream>
#include <map>
#include <string>

using namespace std;

template<class T> void print(map<string, T>& m){
	for (const auto& [key, value] : m){	// [[C++17]]
		cout << key << ": " << value << endl;
	}
}
int main(int argc, char** argv){

	map<string, string> person{
		{"name", "Kyohei, Takahashi"},
		{"nickname", "kcrt"},
		{"addr", "kcrt@kcrt.net"},
		{"age", "34"}
	};
	// この初期化は[[C++11]]から
	print(person);

	// 取得
	cout << person["nickname"] << endl;
	cout << person["nokey"] << endl;	// 存在しない場合はデフォルト値で作られてしまう
try{
	cout << person.at("nokey2") << endl; // out_of_range[[ERROR]]
}catch (...){
	cout << "Exception" << endl;
}
	
	// 追加
	person["birthday"] = "1984-09-24";

	person.insert(make_pair("A", "a"));
	person.insert(make_pair("A", "b"));	// insertはすでにキーがあると上書きしない [[注意]]
	person.emplace("B", "d");	// [[C++11]]
	person.insert_or_assign("B", "c");	// あれば上書き[[C++17]]
	person.try_emplace("B", "e");	// [[C++17]] moveしない
	print(person);

	// 削除
	person.erase(person.find("age"));
	if(0){
		person.clear();	// 全消去
	}
	// 要素数
	cout << "size: " << person.size() << endl;
	// キー存在確認
	cout << person.count("age") << endl;	// 1 or 0 size_t
	// 結合
	map<string, int> dict1{{"a", 1}, {"b", 2}};
	map<string, int> dict2{{"a", 3}, {"d", 4}};
	dict1.merge(dict2);		// [[C++17]] 元々の方が優先
	dict1.insert(dict2.begin(), dict2.end()); // [[C++17]]以前ならこれでもOK
	print(dict1);
	
	// 走査
	for (const auto& [key, value] : person){	// [[C++17]]
		cout << key << " is " << value << endl;
	}
	for (auto it = person.begin(); it != person.end(); it++){
		cout << it->first << " is " << it->second << endl;
	}


}

// g++ helloworld.cpp -o helloworld(実行ファイル名)
// clang++ helloworld.cpp -o helloworld
//	--std=c++11フラグなどでC++のバージョンを指定できる
