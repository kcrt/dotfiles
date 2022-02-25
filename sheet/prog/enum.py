#!/usr/bin/env python3

from enum import Enum, IntFlag, auto, unique


class Fruits(Enum):
    Apple = 1
    Banana = 2
    Orange = 3
    Kiwi = 3    # デフォルトでは値の重複を許す


myfruit = Fruits.Banana
myfruit          # => Fruites.Banana
myfruit.name     # => Banana
myfruit.value    # => 2
Fruits(3)        # => Fruites.Orange
Fruits["Orange"]  # => Fruites.Orange
myfruit is Fruits.Banana
myfruit == Fruits.Banana  # is か == を使用して比較
print(Fruits.Banana == 2)   # False[[注意]] Enumの代わりにIntEnumを使用すると比較できる


@unique
class Colors(Enum):
    Red = 1
    # Blue = 1      [[ERROR]] @uniqueでは同じ値は許されない


class Pref(Enum):
    Hokkaido = auto()
    Aomori = auto()         # auto()は順番に大きいintを返してくれる


# ビット演算を出来るEnum(Flag, IntFlag)
class Perm(IntFlag):
    R = 4
    W = 2
    X = 1
    RWX = 7


file_perm = Perm.R | Perm.W
if Perm.R in file_perm:
    print("File is readable!")

# 他にOrderedEnum, DuplicateFreeEnum
