#!/usr/bin/env julia

'x'		# Char
'ðº'	# Char
'\u0078'	# Char
typeof('x')		# => Char

Int('x')		# 120
Char(120)		# 'x'
Char(0x1f37a)	# 'ðº'
isvalid(Char, 0x1f37a)	# true (valid character)

str = "Hello\n"
str2 = """
	This is a very
	long string.
	"""	# ããã¨åãã¬ãã«ã®ã¤ã³ãã³ãã¯ç¡è¦ããã
print(str2)
str[1]		# 'H'
str[2]		# 'e'
str[end-1]	# 'o'
str[end]	# '\n
str[2:4]	# "ell"
str[2]		# 'e': Char
str[2:2]	# "e": String

SubString(str, 2, 3)	# str[2:3]
chomp("Hello\n")
chop("Hello")	# "Hell"
strip("   Hello   \n")	# Hello, isspaceãåé¤
strip("abcHellobca", ['a', 'b', 'c'])
# lsstrip, rstrip

# UTF-8
str = "é«æ©"	# 0x E9AB99 E6A98B
str[1]	# => 'é«'
# str[2]	# => StringIndexError
nextind(str, 1)	# => 4
str[4]	# => 'æ©'

for c in str
	println(c)
end


# concat
a = "Hello, "
b = "kcrt"
println(a * b * ".")
println("Good morning, $b.")
println("1 + 2 = $(1 + 2)")

# strcmp
print("abc" < "def")


'o' in "Hello"
occursin("world", "Hello, world.")
findfirst(isequal('o'), "Hello")
findfirst("ll", "Hello")	#=> 3:4
# findlast
startswith("Hello, world", "Hello")
endswith("Hello, world", "world")

repeat("abc", 10)
join(["apples", "bananas", "pineapples"], ", ", " and ")

length(str)
ncodeunits(str)


# replace
replace("Hello, world", "world" => "Japan")

