print("Hello, world!")
require("tidyverse")

# vector, matrix, data.frame, list, array, pairlist, ...

# まず理解すべきなのはvector
# vector はすべてが同じ型からなる1次元配列である。
c(1L, 2L, 3L)	# => 1 2 3からなるvector(integer)
1:3					# => 1 2 3 の vector(integer)
c(1, 2, 3)			# vector(double) Rの数値の標準はdouble
2					# 実はこれも要素が1のベクトル

# 最も大きい型に自動的に設定拡張される。
typeof(c(TRUE, FALSE))	# => logical
typeof(c(TRUE, 1L))		# => integer
typeof(c(TRUE, 1))		# => double
typeof(c(TRUE, "a"))	# => character
# NULL < raw < logical < integer < double < complex < character < list < expression

a = 1:5
a[1]				# 最初の要素 (1-origin)
a[1:3]				# 1-3番目の要素
a[c(1, 3)]			# 1, 3番目の要素 (ベクトルを指定)
a[c(-1, -2)]		# 1, 2番目*以外*の要素 (負のベクトルを指定)
a[c(T,F,T,T,F)]		# TRUE(例では1,3,4)に対応する要素 (logicalベクトルを指定)
head(a, 1)			# 最初の1要素
tail(a, 1)			# 最後の1要素

2:4 * 3:5			# 6 12 20 (2x3, 3x4, 4x5)

# 要素のコピー
b = a				# これだけでOK

# 要素長
length(a)

# 一致の検索
a %% 2 == 1			# T, F, T, F, T (logical vector)
sum(a %% 2 == 1)	# 奇数の個数

# 存在確認
match(5, a)			# あればindex, なければNA
5 %in% a			# 存在をT/Fで返す

# 要素の追加・削除
print("add")
a
a[10] = 2			# 自動的に要素が10個まで拡張される
					# (間はNAになる)
a	# 1  2  3  4  5 NA NA NA NA  2
append(a, b)		# 結合した配列を返す(もとの配列は変わらない)
append(a, 100, after=2)	# 第2要素の後に100を追加

a = a[c(-3, -4)]	# 要素3, 4を消去

a[a %% 2 == 1]		# 奇数のみ抽出

# ソート
sort(a)				# ソート済みを取得(元は変わらない)
sort(a, decreasing=T)

# 逆順
rev(b)				# 逆順を取得

# 走査
for(item in a){
	print(item)
}

# function apply
"f apply"
a = 1:5
# ベクトル対応の関数ならそのまま使用できる。
sqrt(a)		# 1.00 1.41 1.73 2.00 2.24
# applyファミリー(apply, lapply, tapply...)
# vector に関数を適応する場合はsapplyが便利
twice = function(x) { return(x * 2) }
sapply(a, twice)	# 2 4 6 ...
Map(twice, a)		# listを返す
map(a, twice)		# listを返す [[tidyverse]]
map_dbl(a, twice)	# vector(double)を返す [[tidyverse]]

# filter
"filter"
a[a > 3]
isodd = function(x) {return(x %% 2 ==1)}
Filter(isodd, a)
keep(a, isodd)		# [[tidyverse]]
discard(a, isodd)	# keepの逆 [[tidyverse]]

# reduce
"reduce"
Reduce(`*`, a)
reduce(a, `*`)	# [[tidyverse]] 


# もともとMap, Filter, Reduceがあるが、関数が第1引数なので
# パイプ演算子と組み合わせれない
# purrr[[tidyverse]]の関数なら下記のように出来る
a %>% keep(isodd) %>% map(twice) %>% reduce(`*`)


# min max
max(a)
min(a)
which.max(a)	# index
which.min(a)	# index

#all, any
all(a > 3)
any(a == 2)


# list
# 型も要素数も同じでなくても良い
# list自体を入れ子にすることも出来る
l = list(TRUE, 1:5, 3.14, "Hello")
l[1]	# 第1要素 (リストとして) 
l[[1]]	# 第1要素
names(l) <- c("a", "b", "c", "d")
l$a	# namesで名前を付けて、$や[['']]でアクセス可能
l[["a"]]
is.list(iris)	 # data.framdも一種のリスト

# array 多次元のvector
# 要素はすべて同じ型である必要がある
arr = array(1:9, dim=c(3, 3))
arr[0] = "a"
arr

# matrix
matrix(1:9, 3, 3)	# 3 x 3のmatrix
is.array(arr)	# matrix はarrayでもある
