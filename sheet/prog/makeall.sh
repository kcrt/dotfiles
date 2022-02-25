#!/usr/local/bin/zsh

for i in *.(c|cpp|go|py|jl|r|js); do
	echo "$i"
	gvim "$i" -c ":set nonumber" -c ":colorscheme morning" -c ":colorscheme macvim" -c :TOhtml -c :wq -c :qall
	sleep 1
done
mv *.html result
