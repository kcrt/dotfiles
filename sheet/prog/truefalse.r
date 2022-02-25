
print("Hello, world!")

truefalse <- function(x) {
	result = ifelse(eval(x), "true", "false")
	print(paste0(x, " is ", result))
}

print(ifelse(0, "0 is true", "0 is false"))
print(ifelse(1, "1 is true", "1 is false"))
print(ifelse(0.0, "0. is true", "0. is false"))
print(ifelse(1.0, "1. is true", "1. is false"))
print(ifelse(NaN, "nan is true", "nan is false"))
print(ifelse(NA, "na is true", "na is false"))
print(ifelse(Inf, "inf is true", "inf is false"))
print(ifelse("0", "string0 is true", "string0 is false"))
print(ifelse("1", "string1 is true", "string1 is false"))
print(ifelse("A", "stringA is true", "stringA is false"))
print(ifelse("true", "stringtrue is true", "stringtrue is false"))
print(ifelse("True", "stringTrue is true", "stringTrue is false"))
print(ifelse("false", "stringFalse is true", "stringFalse is false"))
print(ifelse("", "nullstr is true", "nullstr is false"))
print(ifelse(c(), "emptyarr is true", "emptyarr is false"))
print(ifelse(NULL, "null is true", "null is false"))

if(NULL){
	print("true!!!")
}else{
	print("false!!!")
}

# R --vanilla < helloworld.r
# Rscript helloworld.r
# R CMD BATCH --vanilla helloworld.R  出力はhelloworld.Routになる
