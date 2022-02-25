#!/usr/bin/env julia

import Printf

# 変数の宣言
x = 32
x = "Hello"
local xx::Int32 = 1

# 変数のスコープ
for i in 1:5
	global y = i
	z = i
end
println(y)	# => ok
# println(z)	# => UndefVarError


# 整数:
# Int8, Int16, Int32, Int64, Int128
# UInt8, UInt16, UInt32, UInt64, UInt128
# Int, UInt (環境で変わる)
# Integer (すべてのIntの親)
# リテラル変数の型は環境によって変わる
typeof(1)		# => Int64 (環境による)
0x20
0b10111100
0xdead_beaf		# _を区切りとして使える
x = typemax(Int64)
x + 1	# => -9223372036854775808: wraparoundh

# BigInt, BigFloat
BigInt(100)
big(100)
parse(BigInt, "12345678901234567890")
parse(BigFloat, "1.2345678901234567890")
big"12345"
big"123.4"

# BigFloatの精度
precision(BigFloat)
setprecision(512) do
	println(big"0.1")
end



# 浮動小数点: Float16, Float32, Float64 (=倍精度)
# AbstractFloat (Floatの親)
x = 0.3	# Float64
1.
2.5e-4
0x1.8p3
float(2)

2.0f3	# fを使うとFloat32
isfinite(x)
isinf(x)
isnan(x)

a = 0.24
Printf.@printf("%f %e\n%g %a\n",
			   a, a, a, a)


eps(Float64)

# 上下限
typemin(Int32)		# => -2147483648
typemax(Int32)		# => 2147483647


# Bool
true || false

# complex
1 + 2im

# 有理数
x = 6 // 9	# == 2 // 3
rationalize(1.5)	# == 3 // 2
numerator(x)	# 2: 分子
denominator(x)	# 3: 分母
float(x)	# 0.66666..
typeof(x)	# Rational{Int64}

# 無理数
typeof(π)	# Irrational{:π}

# 型
typeof(1)	# => Int64
isa(1, Int)	# => true
supertype(Int) # => Signed
using InteractiveUtils	# REPLでは不要
subtypes(Signed)	# => BitInt, Int128, Int64, ...

Int64 <: Integer	# true; "<:" == is a subtype of


# シンボル (Symbol)
:hello
typeof(:hello)	# > Symbol
print(Symbol("hello") == :hello)
Symbol("he", "l", "lo")
my_var = :hello
hello = "Hello, world"
println(eval(my_var))	# my_var => :hello => "Hello, world"
#=
Multi line Comment
is 
here
=#
# 定数
const c = 3
