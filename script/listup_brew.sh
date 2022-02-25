#!/bin/bash

n=`brew list | wc -l`
i=0
echo "There are $n items in brew list." > /dev/stderr
for brewname in `brew list`; do
	i=$((i+1))
	if [ $(($i % 10)) -eq 0 ]; then
		/bin/echo -n "$i... " > /dev/stderr
	fi
	info=`brew info $brewname`
	summary=`echo "$info" | head -n2 | tail -n1`
	url=`echo "$info" | head -n3 | tail -n1`
	/bin/echo "$brewname	$url	$summary"
done
/bin/echo "Done." > /dev/stderr

n=`brew cask list | wc -l`
i=0
echo "There are $n items in brew cask list." > /dev/stderr
for brewname in `brew cask list`; do
	i=$((i+1))
	/bin/echo "$i / $n" > /dev/stderr
	info=`brew cask info $brewname`
	summary=`echo "$info" | head -n2 | tail -n1`
	url=`echo "$info" | head -n3 | tail -n1`
	/bin/echo "$brewname (cask)	$url	$summary"
done
/bin/echo "Done." > /dev/stderr
