
commandArgs()
# [1] "/(略)/bin/R"
# [2] "--vanilla"
# [3] "--args"
# [4] "hello"

commandArgs(trailingOnly=T)
# [1] "hello"

# R --vanilla --args hello < arg.r
# Rscript arg.r hello
