#!/usr/bin/env python3

a = 10
fruits = ["apple", "banana", "fig"]

print("a"); print("b")

# == if ==
if a < 10:
    print("less than 10.")
elif a == 10:
    print("equal to 10.")
else:
    pass            # 何もしない時もpassが必要

# == for each ==
for i in range(5):
    print(i)        # => 0, 1, 2, 3, 4

for food in fruits:
    print(food)

for i in range(5):
    if i == 3:
        continue    # 次のループへ
    elif i == 4:
        break       # このforを終わる
else:
    print("Yes!")   # ループを使い切ったときに実行(breakで抜けると実行されない)

# == loop ==
while a > 0:
    a -= 1

while a < 10:
    a += 1
    if (a == 4):
        continue
    if (a == 6):
        break

# infinite loop
while True:
    pass

# == switch (select case) ==
# Pythonにはswitchに相当する構文はない。
# if-elif-elif-...を駆使すること。


# == goto ==
# ない

# == with ==
with open("/tmp/myfile", mode="w") as f:
    f.write("Hello")
# withを使用することで終了処理を簡素化できる。
# 例えば、上記であれば、ファイルのクローズなどを行わなくて良い

# == exceptionは別ファイル
