#!/usr/bin/env python3


def myHello(greeting, name="kcrt"):
    return f"{greeting}, {name}."


# 型ヒント付きの時
def myHello2(greeting: str, name: str = "kcrt") -> str:
    return f"{greeting}, {name}."


myHello("Hello", "John")  # => Hello, John.
myHello("你好")   # => 你好, kcrt.
myHello(name="Mary", greeting="Good morning")  # => Good morning, Mary.


# TODO: va_arg

# TODO: 複数の値を返す関数
def add_sub(a, b):
    return (a + b, a - b)

print(add_sub(3, 5))

# == decorator == 
def my_decorator(func):
    def my_function(*args, **kwargs):
        print("--Start--")
        func(*args, **kwargs)
        print("--End--")
    return my_function

@my_decorator
def Hello():
    print("Hello")
# Hello = my_decorator(Hello) となる。

Hello()

# TODO: position only parameter (3.8) 
