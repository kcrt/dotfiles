#include <iostream>
#include <boost/algorithm/string.hpp>
using namespace std;
using namespace boost;

using namespace std::string_literals;
int main(int argc, char** argv){

	
	cout << u"本日" << endl;
	cout << U"本日" << endl;
	cout << u8'A' << endl;

	std::cout << R"(\a\b\c\")" << std::endl;
	std::cout << "abcde"s.substr(2,2) << std::endl;
	std::cout << "ab"s + "cd"s << std::endl;
	std::cout << "ab"s.length() << std::endl;
	std::cout << ("ab"s == "ab") << std::endl;

	std::cout << "----" << std::endl;
	std::cout << "abcde"s.find("cx") << std::endl;
	std::cout << "abcde"s.replace(1, 2, "x") << std::endl;

	// boost
	auto s = " abc "s;
	to_upper(s);
	cout << s << endl;
	trim_right(s);
	cout << s << endl;
	trim(s);
	cout << s << endl;
	cout << boost::contains(s, "BC") << endl;
	cout << boost::icontains(s, "bc") << endl;
	cout << starts_with("abc"s, "ab"s) << endl;
	cout << starts_with("abc"s, "ax"s) << endl;

	s = "Hello, world"s;
	boost::replace_first(s, "l", "X");
	cout << s << endl;
	boost::replace_all(s, "l", "X");
	cout << s << endl;
	vector<string> v;
	s = "abc|def|xyz"s;
	split(v, s, boost::is_any_of("|"));
	for (auto x : v){
		cout << x << endl;
	}

}
