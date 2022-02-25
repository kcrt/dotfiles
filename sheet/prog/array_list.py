#!/usr/bin/env python3

# 配列に相当する物は、List, Tuple, Arrayの3種類がある。

from array import array
from functools import reduce
from operator import mul

# === List ===
# 最もよく使用される
l = ['a', 'b', 'c', 'd', 'e', 1, 2, 3]  # 同じ型でなくても良い
l[0]                # => a : 0番目の要素にアクセス
l[-1]               # => 3 : 最後の要素
l[-2]               # => 3 後ろから2番目の要素
l[1:3]              # => ['b', 'c'] : スライス l[1], l[2]からなる新しいリスト
l[3:]               # l[3]から最後まで
l[:]                # 全部のコピー

[]                  # 空のリスト
['A', 'B', 'C'] * 5  # => ['A', 'B', 'C', 'A', 'B' ...]

l2 = l              # l2はlと同じ物をさす。コピーではない！[[注意]]
l2[0] = 'x'         # l2を変更したつもりでも…
l[0]                # => x : lも変更されてしまう！

# 要素のコピー
new_l = l[:]           # スライスか、l.copy()を使って新しいListを得る
new_l[1] = 'z'
l[1]                # => b : これならlは変更されない

# 要素数
len(l)

# 一致の検索
l.count('d')        # 'd'の数を数える

l.index('d')        # => 3 : 最初の'd'の場所、見つからなければ[[ERROR]] ValueError

if 'd' in l:
    pass            # in で存在確認
elif 'd' not in l:
    pass

# 要素の追加: appendとextendがある
a1 = ['A', 'B', 'C']
a2 = ['A', 'B', 'C']
a1.append(['X', 'Y'])   # ['A', 'B', 'C', ['X', 'Y']]
a2.extend(['X', 'Y'])   # ['A', 'B', 'C', 'X', 'Y']

l.append('A')           # 配列でなければappendを使用する
l += ['B', 'C']         # += は extendと同じ


# 先頭/任意の場所への追加
l.insert(0, 'Z')        # 要素を追加 (0で先頭)

# 削除
s = l.pop()             # **最後**の要素を取り出して削除
s = l.pop(0)            # 0 (= 最初)の要素を取り出して削除
l.remove('A')           # 最初の'A'を見つけて消去 ないとValueError[[ERROR]]
del l[3:5]              # 要素3, 4を消去
l.clear()               # 全消去

l = list(range(10))     # [0, 1, 2, ..., 8, 9]
# range()

# ソート: PythonはStableソート
ll = sorted(l)          # ソートされたもの取得
l.sort()                # そのものをソート
l.sort(reverse=True)    # 降順にするにはreverse=True
# カスタムソートは see: https://docs.python.org/ja/3/howto/sorting.html#sortinghowto

# 逆順
ll = reversed(l)
print(ll)               # sortedと違い、イテレータを返す
ll = list(ll)           # これで、通常のリストになる。
l.reverse()             # そのものを逆順に


# 走査
for val in l:
    print(val)

for i, v in enumerate(l):
    print(i, val)

l = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# map (function applied array)
l2 = map(lambda x: x * x, l)
# for v in l2:
#    print(v)
print(l2)
# l2[2]      # [[ERROR]] Mapオブジェクトなので要素でのアクセスは出来ない
l2 = list(l2)       # Listに変換
print(l2[2])


# filter
l2 = filter(lambda x: x > 5, l)
print(l2)
l2 = list(l2)       # Map同様にListに変換

# reduce
print("reduce")
print(l2)
print(reduce(mul, l2, 1))

# 最大・最小
ll = [1, 2, 3, 4]
max(ll)  # => 4
min(ll)  # => 1


# リスト内包表記
# Pythonの強力な機能 [[重要]]
# mapにもfilterにもなる
l2 = [x * x for x in l if x > 5]
# [ 計算式 for 仮引数 in 対象のリスト if 条件 ] (if 条件は省略可)
print(l2)
# []の代わりに () だと generator (必要時に計算)
l3 = (x * x for x in l if x > 5)
print(l3)

# all
ll = [20, 20, 30]
if all(x > 10 for x in ll):
    print("all > 10")

# any
if any(x == 20 for x in ll):
    print("There is 20.")

# === Tuple ===
# イミュータブル(immutable; 変更を許してくれない)なリスト
t = (1, 2, 3, 4, 5)
print(t[4])     # リスト同様に使用できるが、
# t[1] = 10     # [[ERROR]] 変更が必要になる動作は
# t.sort()      # [[ERROR]] 行うことが出来ない
ll = list(t)    # 変更したい場合はリストに変換すれば良い
ll.sort()
t = tuple(ll)   # listからtupleへ

# タプルは代入にも便利
(a, b, c) = (1, 3.2, "Hello")

# === array ===
# 大量の数値を格納するときなどに使う。
# おそらくほとんどのケースで、numpyを使う方がよいので、そちらを参照されたし。
arr = array('i', [1, 2, 3, 4, 5])
arr2 = array('u', "Hello")
# 'b'/'B': singed/unsigned char, 'u': Py_UNICODE
# 'h'/'H': signed/unsigned short, 'i'/'I': signed/unsigned int
# 'l'/'L': signed/unsigned long, 'q'/'Q': signed/unsigned long long
# 'f': float, 'd': double
print(arr.itemsize)     # sizeof(signed int)
arr.append(6), arr.count(3)     # Listと同様にいろいろ使用できる
arr.byteswap()          # リトルエンディアンとビックエンディアンの変換

arr2.fromunicode("Hello")   # こんな名前だが、動作はextend

# array.fromfile(fileobject, n) / array.tofile(fileobject)
