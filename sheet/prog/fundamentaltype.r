
require("tidyverse")

# 他の言語と違って、型の大きさ的な物がある、
# logical -> numeric(integer, double) -> complex -> characterの順に"大きい" 

# 整数
x = 32              # これだとdouble
y = as.integer(32)     # これで初めてinteger
32L # もしくはLを付ける

# typeofとmodeで簡単に調べることが出来る
print(typeof(x))    # double
print(typeof(y))    # integer
print(mode(x))      # numeric

# 浮動小数点
d = 3.14
Inf
-Inf
NaN
is.nan(NaN)
is.infinite(Inf)    # 逆はis.finite

a = 0.24
format(a, digits = 1)		# 0.2
format(a, nsmall = 10)		# 0.2400000000
format(a, scientific = T)	# 2.4e-01
# 論理型 真 - TRUE, 偽 - FALSE
x = TRUE
typeof(x)               # logical
x = F                   # T, Fという変数があらかじめあり、使用可能

# 定数
# LETTERS, letters, pi, month.name, month.abb のみが定数としてあるが、新規に定義は出来ない。
print(pi)

# 変数の上限・下限
.Machine$integer.max
# .Machine$integer.min はない (INT_MINはNA(integer)の内部表現として使用されているため)
.Machine$double.eps
.Machine$double.xmin    # C++でいうlower (DBL_MINではない)
.Machine$double.xmax
format(.Machine)

# Rに固有な物としてNA(欠損値)がある。
# doubleのNAや、characterのNAなど型ごとに内部では違う。
NA                  # logicalのNAだが、状況に応じて適切な型に変換される。
NA_integer_			# 明示的に型を指定する場合：NA_real_, NA_complex_, NA_character_
is.na(NA)           # true
is.nan(NA)          # false
is.na(NaN)          # true [[注意]]

# dataframe
print(iris)
quantile(iris$Sepal.Length)
iris %>%
	group_by(Species) %>%
	summarize(n = n(),
			  Length_mean = mean(Sepal.Length)) %>%
	print()
	# [[tidyverse]]



# 永続代入
setx <- function(){
	x1 <- 1
	x2 <<- 2
}
setx()
x1	# error
x2
