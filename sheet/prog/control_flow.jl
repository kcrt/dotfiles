#!/usr/bin/env julia

# 複合式
z = begin
    x = 1
    y = 2
    x + y
end

a = 10
fruits = ["apple", "banana", "fig"]

# == if ==
if a < 10
    println("less than 10.")
elseif a == 10
    println("equal to 10.")
else

end

try
    # ifの条件は必ずBoolでないといけない
    if 1    # TypeError
        println("true!")
    end
catch

end

# == 3項演算子 ==
println(a < 0 ? "negative" : "not negative")

# == 短絡評価 ==
f(x) = begin println(x); return true end

false && f("Won't be evaluated")
true || f("Won't be evaluated")

# bitwiseだと評価される
false & f("Will be evaluated")
true | f("Will be evaluated")

# == for (each) ==
for i = 1:5
    println(i)  # 1, 2, 3, 4, 5
end

for i in 1:5    # in, ∈も同様に使用可能
    println(i)
end

for val in fruits
    println(val)
end
x = 1
for x = 1:3
	# forのxと外のxは別物
end
println(x)  # 1

function aaa()
	x = 1
	for outer x = 1:3
		# outer: forのxと外のxは共通
	end
	println(x)  # 3
end

# == break, continue
for i in 1:10
    if i == 4
        continue    # 次のループへ
    elseif i == 5
        break       # ループ終了
    end
end

# == nested for
for i = 1:3, fruit in fruits
    println(i, fruit)
    # 1apple, 1banana, 1fig, 2apple, ...
end

# == loop ==
println("loop")
while a > 0
    println(a)
    global a -= 1
end

while true
	break
end


# switch


# goto
function my_goto_func()
    @goto mylabel

    @label mylabel
    return true
end
