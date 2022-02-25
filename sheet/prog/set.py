#!/usr/bin/env python3

# https://devdocs.io/python~3.7/library/stdtypes#types-set

# 集合
# setとfrozenset(変更不可)がある
mySet = set(['Apple', 'Banana', 'Kiwi'])
# または
mySet = {'Apple', 'Banana', 'Kiwi'}
len(mySet)    # => 3
mySet.add("Orange")
mySet.add("Orange")  # 何回追加しても
mySet.add("Orange")  # 重複しては入らない
mySet           # => {'Apple', 'Banana', 'Kiwi', 'Orange'}

mySet.discard("Apple")
mySet.remove("Banana")
# discard はなくてもエラーにならない
# remove はないとKeyError[[ERROR]]
# 一度に複数削除する .differece_update(_set_) または mySet -= _set_も使える
mySet   # => {'Kiwi', 'Orange'}
mySet.update({'Kiwi', 'Peach', 'Mango'})
# または mySet |= {'Kiwi', 'Peach', 'Mango'}
mySet   # => {'Mango', 'Orange', 'Peach', 'Kiwi'}

# 内包表記も使用できる
{f"**{x}**" for x in mySet}

myItem = mySet.pop()    # なにが出てくるかは**運次第**
mySet.clear()   # すべて消去

emptySet = set()    # "{}"だとdictになる

aSet = {1, 2, 3, 4, 5}
bSet = {2, 4, 6, 8, 10}

3 in aSet       # => True
6 not in aSet   # => True

# 和集合：A∪B
aSet.union(bSet)  # => {1, 2, 3, 4, 5, 6, 8, 10}
# または
aSet | bSet

# 積集合・共通部分：A∩B
aSet.intersection(bSet)  # => {2, 4}
# または
aSet & bSet

# 差集合: A ∖ B (Aのうち、Bに含まれていないもの)
aSet.difference(bSet)    # => {1, 3, 5}
# または
aSet - bSet

# 対象差：A△B
aSet.symmetric_difference(bSet)  # => {1, 3, 5, 6, 8, 10}
# または
aSet ^ bSet

aSet.issubset(bSet)     # A⊆B
# または
aSet <= bSet

aSet.issuperset(bSet)   # A⊇B
# または
aSet >= bSet

aSet.isdisjoint(bSet)   # A∩B=∅
