#!/usr/bin/env julia

try
    println("Hello, world")
    throw(ErrorException("Exception!"))
catch err
    if isa(err, DomainError)
        println("Domain Error!")
    elseif isa(err, ErrorException)
        println(err.msg)
    end
finally
    print("Operation finished.")
end

try
    # ErrorExceptionをthrowする関数
    error("Error occured!")
catch;end

# ユーザー定義例外
struct MySpecialError <: Exception
end
# 主な例外
# ArgumentError, BoundsError, CompositeException, DivideError, DomainError, EOFError, ErrorException, InexactError, InitError, InterruptException, InvalidStateException, KeyError, LoadError, OutOfMemoryError, ReadOnlyMemoryError, RemoteException, MethodError, OverflowError, Meta.ParseError, SystemError, TypeError, UndefRefError, UndefVarError, StringIndexError
