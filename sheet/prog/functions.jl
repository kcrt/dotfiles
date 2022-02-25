#!/usr/bin/env julia

# 関数の宣言
function myHello(greeting, name)
	return "$greeting, $name."
end

myHelloX(x, y) = "$x, $y."

# 型、デフォルト引数付き
function myHello2(greeting::String, name::String = "kcrt")::String
	return "$greeting, $name."
end

# オーバーロード
function myHello2(name::String)::String
	return "Hello, $name"
end

methods(myHello2)	# => 2 methods ... (略)


myHello("Hello", "John")	# => Hello, John
myHello2("你好")			# => 你好, kcrt.

# キーワード引数(通常引数と「;」で区切る)
function myHello3(greeting::String; name::String = "kcrt", kwargs...)::String
	return "$greeting, $name."
end
myHello3("こんにちわ", name="Tom")

# va_arg
function bar(a, b, x...)
	println(x)
end
bar(1, 2, 3, 4)	# => x = (3, 4)となる


# 複数の値を返す関数
function foo(a, b)
	a + b, a * b
end
x, y = foo(2, 3)

# === do記法 ===
# func(A, B, C) do xxx
#   ...
# end
# は、
# func( xxx -> ..., A, B, C)
map([1, 2, 3]) do x
	return x * 2
end	# => [2, 4, 6]

map(x -> x * 2, [1, 2, 3])	# 同じ


# === ドット(.)記法 ===
twice(x) = x * 2
twice.([1, 2, 3])	# => [2, 4, 6]
parse.(Int, ["1", "2"])	# => [1, 2]
