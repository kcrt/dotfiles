#!/usr/bin/env python3

from collections import defaultdict, OrderedDict

# python ではdictと呼ばれる
person = {
    "name": "Kyohei, Takahashi",
    "nickname": "kcrt",
    "addr": "kcrt@kcrt.net",
    "age": 34
}
my_dict = dict(one=1, two=2, three=3)   # これでも作れる

person["nickname"]  # => "kcrt"
# person["nokey"]   # [[ERROR]] KeyError
person.get("nokey", "default")   # なければ引数で指定したもの(省略時None)を返す (例外にならない)

person["birthday"] = "1984-09-24"   # 辞書に追加・変更
del person["age"]                   # 辞書から削除
my_item = person.pop("addr")        # 取得して削除
len(person)         # => 4 : 項目の数

"age" in person     # キーが含まれているかの確認

# 結合
dict1 = {"a": 1, "b": 2}
dict2 = {"a": 3, "d": 4}
dict1.update(dict2)     # dict1 += dict2的な
print(dict1)

# 走査
for (key, value) in person.items():
    print(f"{key} is {value}")
# もしくは
for key in person.keys():
    print(f"{key} is {person[key]}")
# もしくは
for value in person.values():
    print(f"{value}")

# 内包表記
# 配列と同じく内包表記が便利
# { キー: 値 for 仮引数 in 対象のリスト if 条件 } (if 条件は省略可能)
myperson = {name: value.upper() for (name, value) in person.items()}

# defaultdict
mydict = defaultdict(int)
print(mydict["a"])  # => 0 : エラーにならない
for c in ["aa", "bb", "cc"]:
    mydict[c] += 1  # 初めてのアクセス時に要素が出来る

# defaultdict(int)のintは型名でなく関数
# アイテムがなければint() すなわち 0をセットする
# defaultdict(lambda: random.randint(1, 10))なんて事も出来る

# OrderedDict
# defaultdictと違い、ordereddictでないのはこちらの方が新しいから(see: naming_rule)
mydict = OrderedDict()
mydict["a"] = 1
mydict["b"] = 1
mydict["c"] = 1
mydict.keys()    # => 必ず追加した順になる
# 順番が意味を持つjsonファイルなどを扱う際に便利(see: json)
