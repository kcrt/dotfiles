
a = 10
fruites = c("apple", "banana", "fig")

print("a"); print("b")

# if
if (a < 10){
	print("less than 10.")
}else if (a == 10){
	print("equal to 10.")
}else{

}

# 内部的には関数で格納されている。
"if"(1 + 1 == 2, print("two"))


# foreach
for(i in 1:5){
	print(i)	# 1 2 3 4 5
}

for(food in fruites){
	print(food)
}

# break
for(i in 1:5){
	if (i == 3) {
		next	# continueに相当
	}else if (i == 4){
		break
	}
}

# loop
while(a > 0){
	a <- a - 1
}


# infinite loop
repeat {
	break
}

# switch
# Rではswitchは単なる関数である。
switch(2, "a", "b", "c") # => "b"
switch(fruites[1],
	apple = "red",
	banana = "yellow",
	fig = "pink",
	"unknown"	# ここがdefaultにあたる
)	# => red


# R --vanilla < helloworld.r
# Rscript helloworld.r
# R CMD BATCH --vanilla helloworld.R  出力はhelloworld.Routになる
