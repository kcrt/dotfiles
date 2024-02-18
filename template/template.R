require("tidyverse")

data_raw <- read.xls("filename.xls", sheet="Data", na.strings=c("#N/A", "#VALUE!"), fileEncoding="UTF-8")

# vim: filetype=r
