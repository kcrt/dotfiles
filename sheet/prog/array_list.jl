#!/usr/bin/env julia

# === Array ===
l = [1, 2, 3]	# (3 x 1) Array{Int64,1}
l[1]	# => 1, 1-origin
l[end]	# => 3, 最後の要素
l[1:end]# => 要素すべて (部分配列)
l[:]	# => すべての要素のコピー
view(l, 1:2)	# => 要素1, 2の参照部分配列 (変更できる)
lv = @view l[1:2] # 同上
l2= [1			# ,と同じ
	 2
	 3]

# コピー
l[:]	# => すべての要素のコピー

# 要素数
length(l)	# => 3 : 要素数
size(l)		# => (3,) 

# 検索
findfirst(isequal(2), l)	# =>2, なければnothing
findnext(isequal(2), l, 1)	# pos指定 
# findlast, findprev, findall
# isequal(val), iseven, isodd

# 存在確認
in(1, l)	# => true
1 in l
1 ∈ l


# 要素の追加
# 「!」は対象そのものを変更する関数についている
push!(l, 4, 5)	# l = [1, 2, 3, 4, 5]
println(l)
append!(l, [-1, -2])	# -1, -2を末尾に追加 (Pythonのappend)
println(l)

# 先頭/任意の場所への追加
insert!(l, 1, 10)	# 指定の場所に追加: 1が先頭
pushfirst!(l, 5, 10)	# 5, 10を先頭に追加

prepend!(l, [8, 9])	# appendの先頭バージョン
println(l)
# 削除
println(pop!(l))	# 末尾の要素を取得して削除
println(popfirst!(l))	# 先頭要素
deleteat!(l, 5)		# 5番目の要素を削除

# 
# ソート
println("sort")
println(l)
sort!(l)
println(l)
sort!(l, by = x -> abs(x))	# by = で方法を指定
println(l)

# 走査
println("run")
for i in l    # =, in, ∈も同様に使用可能
    println(i)
end


# 逆順
l = [1, 2, 3, 5, 10]
reverse(l)
reverse!(l)
for i in Iterators.reverse(l)
	println(i)
end

twice = (x:: Int) -> x *2
# map (function applied array)
println("map: ", map(twice, l))
ll = map(twice, l)
# broadcastでもよい
println(twice.(l))
println(l * 2)       # そもそもjuliaならこれでも良い
println(l .* 2)      # そもそもjuliaならこれでも良い
# filter
l3 = filter(isodd, l)	# 奇数のみ取得
println(l3)
# filter!を使用すれば、配列自体を変更できる。
# reduce
prod = reduce(*, l)     # *はjuliaでは関数
println(prod)
# 最大・最小
println(maximum(l))			# => value
println(findmax(l))			# => (value, index)
println(argmax(l))			# => index
println(extrema(l))			# => (min, max)
# minimum, findmin, argmin

# リスト内包表記
println([ n * n for n in l if n > 2 ])
g = ( n * n for n in l if n > 2 ) 	# generator
print(collect(g))	# collectでrangeやgeneratorをArrayに変換

# all
all(isodd, l)
# any
any(isodd, l)


# 多次元配列
m = [1 2 3]		# (1 x 3) Array{Int64,2}
n = [1 2 3		# (3 x 3)
	 4 5 6
	 7 8 9]
n2 = [1 2 3; 4 5 6; 7 8 9]	# 上と同じ
n[1, 1]			# => 1

length(n)	# => 9
size(n)		# => (3, 3)

# 行列の計算
n * n	# 行列の積
n .* n	# アダマール積
log.(n)	# .付き関数はすべての要素に関数を適応する

# 型の指定
Float64[1, 2]		# Floatの配列

# === Tuple ===
# immutable
t = (1, 2, 3, 4, 5)
t[1]	# => 1
(1, )	# 要素数1のTuple
typeof(t)	# => NTuple{5, Int64}

t = ("kcrt", 32)
typeof(t)	# => Tuple{String,Int64}

# 名前付きタプル
t = (a = 1, b = "Hello")
t.a		# => 1
typeof(t)	# => NamedTuple{(:a, :b),Tuple{Int64,String}}

# swap
a = 1; b = 2
a, b = b, a

