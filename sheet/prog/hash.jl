#!/usr/bin/env julia

# Dict
person = Dict(
	"name" => "Kyohei, Takahashi",
	"nickname" => "kcrt",
	"addr" => "kcrt@kcrt.net",
	"age" => 34
)
println(person)
keytype(person)		# 型を取得
valtype(person)	# 
# 型は推測される(上記だとDict{String, Any})
# {"a" => 1, "b" => 2} という書き方があったが[[obsolete]]

# tupleの配列でもよい。
# また、型を指定することも出来る。
my_dict = Dict{String, Int64}([("a", 1), ("b", 2)])
Dict(:a => 1, :b => 2)	# keyにシンボルを使用することも出来る。
# データの取得
println(person["nickname"])	# => "kcrt"
# person["nokey"]	# [[ERROR]] KeyError
get(person, "nokey", "default")	# 無ければデフォルトを返す
get!(person, "nokey", "default")	# 無ければデフォルトを格納

# 辞書に追加
person["birthday"] = "1984-09-24"
# 辞書から削除
delete!(person, "age")
# 取得して削除
my_item = pop!(person, "age", "default")	# 取得して削除(defaultは省略可)

# 項目数の取得
println(person)
println("length: ", length(person))

# キーの有無の確認
haskey(person, "name")
println("name" in keys(person))

# 結合
dict1 = Dict("a" => 1, "b" => 2)
dict2 = Dict("a" => 3, "d" => 4)
d = merge(dict1, dict2)		# 結合Dictを返す
println(d)
# または、
merge!(dict1, dict2)		# dict1に結合
println(dict1)

merge!(+, dict1, dict2)		# Keyが被っている場合は和にする
println(dict1)

# 走査
for (key, value) in pairs(person)	# =, in, ∈ のどれでもOK
    println("$key is $value")
end
for key in keys(person)	# =, in, ∈ のどれでもOK
    println(key)
end
for value in values(person)	# =, in, ∈ のどれでもOK
    println(value)
end
# 内包表記
myperson = Dict(key => uppercase(value) for (key, value) in person)
println(myperson)
# defaultdict, ordereddict

# fruits["Ehime"]		# "=> Mikan": 値の取得
# fruits["Kagawa"] = "Udon"	# 値の設定
# get(fruits, "Hiroshima", "Lemon")	# 取得(デフォルト付き)
# 
# 
# keys(fruits)	# キーの集合
# values(fruits)	# 値の集合


# Pair
mypair = "a" => 1	# Pair{String,Int64}
mypair[1] # => "a"
mypair[2] # => 1

