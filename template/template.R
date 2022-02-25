library("gdata")
library("agricolae")
library("ggplot2")
source("~/etc/src/functions.R")

data <- read.xls("filename.xls", sheet="Data", na.strings=c("#N/A", "#VALUE!"), fileEncoding="UTF-8")
# data <- read.csv("filename.csv", na.strings=c("#N/A", "#VALUE!"))
str(data)

png("filename.png")
plot(data$value~data$group)


# vim: filetype=r
