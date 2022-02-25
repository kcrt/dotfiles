#include <iostream>
#include <complex>

int main(int argc, char** argv){

	std::cout << "Hello, world!" << std::endl;
    using namespace std::complex_literals;

	//std::complex<double> z = 1. + 2i;
	std::complex<double> z(1., 2.);
	std::cout << z.real() << std::endl;
	std::cout << real(z) << std::endl;
	std::cout << z.imag() << std::endl;
	std::cout << imag(z) << std::endl;

	std::cout << conj(z) << std::endl;
	std::cout << sqrt(-1+0i) << std::endl;
	return 0;

}

// g++ helloworld.cpp -o helloworld(実行ファイル名)
// clang++ helloworld.cpp -o helloworld
//	--std=c++11フラグなどでC++のバージョンを指定できる
