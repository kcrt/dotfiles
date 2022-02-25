#!/usr/bin/env python3

# クラス名は"MyClass"という形式でつける。


class Animal:
    """ Class for living animals """
    class_variable = "クラス変数"
    __private_class_variable = "「__」で始まるとプライベート変数"

    def __init__(self, scientific_name: str = ""):
        self.scientific_name = scientific_name      # インスタンス変数
        self.__is_living = True                     # 「__」で始まるとプライベート変数

    def eat(self, food: str):
        print("{0} is eating {1}.".format(self.scientific_name, food))

    def __str__(self):                              # 「str」のオーバーロード
        return "Animal ({0})".format(self.scientific_name)

    def __lshift__(self, food: str):                     # 「<<」のオーバーロード
        self.eat(food)
        return None

    def __del__(self):
        # デストラクタ (終了時に必ず呼び出されるとは保証されていない)
        print("{0} is dying.".format(self.scientific_name))


class HumanBeing(Animal):       # 継承
    def __init__(self, nickname: str):
        super().__init__("Homo sapiens")
        # もしくは Animal.__init__(self, "Homo sapiens")
        self.__nickname = nickname

    def eat(self, food: str):                       # オーバーライド
        super().eat(food + " with fork")
        # もしくは Animal.eat(self, ...) や self.__class__.__bases__[0].eat(...)


# 多重継承は可能であるが、ここでは触れない。

dog = Animal("Canis lupus familiaris")      # インスタンスの作成
dog.eat("dog food")
dog << "meat pie"                           # オーバーロード済み演算子
print(str(dog))     # => Animal (Canis lupus familiaris)


human = HumanBeing("John")
human.eat("sandwich")
human << "meat pie"                         # これでもHumanBeingのeatが呼ばれる


# オペレーターオーバーロードに使用するメソッド名 see: https://docs.python.jp/3/reference/datamodel.html#special-method-names
# __OPERATOR__の形 (例: __repr__, __eq__)で使用する
# 比較: lt(<), le(<=), eq(==), ne(!=), gt(>), ge(<=); @functools.total_orderinを使用すれば、例えばltとeqを定義するのみですべての比較に対応できる。
# 演算: add, sub, mul, matmul (@), truediv (//), floordiv(/), mod(%), divmod, pow (**), lshift(<<), rshift(>>), and (&), xor(^), or(|)
# 被演算: radd, rsub, ...; A + BはB.radd(A)
# 累算代入: iadd (+=), isub (+=) ...; 定義されてなければA += BはA = A + Bとして計算される
# 単項: neg (-), pos(+), abs, invert(~)
# hash: set, dictなどで使用、整数を返す
# bool, len, contains(in演算子に対応), dir, slots, complex, int, float, round, trunc, floor, ceil, repr, str, bytes, format
# enter, exit (with文で使用)
# copy, deepcopy, getstate, reduce, init, del... (説明省略)


# 特殊なオペレーター
# __getattr__(self, name), __setattr__(self, name, value), __delattr__(self, name)  => dog.attrnameといった形でアクセス
# getattribute はすべての呼び出しで、getattrは未定義アイテムのみで呼び出される
# __getitem__(self, key), __setitem__(self, key, value), __delitem__(self, key), __missing(key) => dog["itemkey"]といった形でアクセス
# __dict__ アトリビュートへのアクセス
# __call__ => インスタンスをdog()の要に関数のように呼び出すとき
# property


class Degree:
    T0 = 273.15

    def __init__(self):
        self.degree = 0
        self._message = "{0:.2f} K"

    def __getattr__(self, name):
        key = name.lower()
        if key == "kelvin":
            return self.degree
        elif key == "celsius":
            return self.degree - self.T0
        elif key == "fahrenheit":
            return self.degree * 9.0 / 5.0 - 459.67
        else:
            raise AttributeError

    def __setattr__(self, name, value):
        print("set to " + name)
        key = name.lower()
        if key == "kelvin":
            if value < 0:
                raise ValueError
            self.degree = value
        elif key == "celsius":
            self.degree = value + self.T0
        elif key == "fahrenheit":
            self.degree = (value + 459.67) * 5.0 / 9.0
        else:
            if name in self.__dict__:
                print(type(self.__dict__[name]))
            self.__dict__[name] = value

    def __call__(self):
        print(self.message)
        print(self.message.format(self.kelvin))

    # propertyを使用するのも便利
    @property
    def message(self):
        print("Yes")
        return self._message

    @message.setter
    def message(self, value):
        print("set")
        self._message = value


temprature = Degree()
temprature.celsius = 36
print("{0.celsius:.2f} C = {0.kelvin:.2f} K = {0.fahrenheit:.2f} F".format(temprature))
temprature()
temprature.message = "It's {0} K!"
temprature()
