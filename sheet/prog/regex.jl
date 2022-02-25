#!/usr/bin/env julia

# r""はregex型
pattern = r"([[:word:]+\.]+)@([[:word:]]+\.[[:word:]]+)"
content = "kcrt@kcrt.net"
typeof(pattern)		# => Regex

# POSIXキャラクタクラス([:alpha:]など)は使用できる

occursin(pattern, content)	# => true
ret = match(pattern, content)	# => RegexMatchを返す
if ret !== nothing
	println(ret.match)
	println(ret.captures[1])
else
	println("No match!")
end

# 名前付きキャプチャ: (?P<name>...)
ret = match(r"(?P<hour>\d\d):(?P<min>\d\d)", "12:34")
ret[:hour]	# => 12

# r文字列はオプションも指定できる
occursin(r"apple"i, "APPLE")
# i: 大文字小文字無視, m: 複数行, s: 単行, x: スペースを無視


# 文字列からRegexを作成する場合は
domain = "kcrt.net"
pat = Regex(".*@$domain")

# 置き換え replace(str, r"pattern1" => s"pattern2")
# s""はSubstituionString型
replace("Hello, world", "world" => "xxxxx")
# => Hello, xxxxx
replace("Hello, world", r"w...d" => s"*\g<0>*")
# => Hello, *world*
