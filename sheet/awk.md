awk '{print $1}' file.txt
awk -F, '{printf "%s, %s\n", $1, $2}' file.txt
awk '/error/ {print $0}' log.txt

# Variables
$0: The entire line.
$1, $2, ...: The fields in the current line.
NF: The number of fields in the current line.
NR: The number of the current line.
FS: The field separator (default is whitespace).
OFS: The output field separator (default is a space).
RS: The record separator (default is a newline).
ORS: The output record separator (default is a newline).