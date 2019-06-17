# **The Dragon Programming Language**

I just made this as an exercise in static compilation. By which I mean this statically compiles to C.

I would use LLVM, but a lot of the higher level stuff I need would be pretty hard to 
implement in LLVM IR but clang gives for free.

**Note: This language is still a work in progress, do not expect everything to work. Contact me if something doesn't work.**
Email: totillity@gmail.com

### How to use

IMPORTANT: **YOU NEED CLANG** (the compiler, which you can get [here](http://releases.llvm.org/download.html#8.0.0)), 
or you can specify the compiler through setting the 
approriate command line flag (see \_\_main__.py) or through passing `compiler='gcc'` or whatever your compiler is in the 
run.py functions.

If the dragon module is in your PYTHONPATH, you can just do `python -m dragon {name of file to run}.drgn`, 
optionally followed by a `--run` flag to immediately run instead of just compiling.

Alternatively, your python script can invoke the functions found in the `dragon.run` file

To see more syntax and usage, look at the examples folder. The run_examples.py file in it can be run to run all the examples.

### Syntax
The syntax is similar to every other c-family language out there.

Comments are a hashtag, followed by a space, followed by everything to the next newline.
Example: `# comment here`

A Program is a collection of top level statements

Valid top level statements are current limited to classes, functions, and hashcodes.

#### Classes

##### Declaration:

`class TestClass<T, K>(BaseClass) { ... }`

The class keyword and the class name is mandatory. 

Any generic arguments the class takes must be valid identifiers, comma separated, and inside the angle brackets.
If no generic parameters are take, the angle brackets maybe omitted.
If the class takes any generic parameters, whenever it appear in code, it must have arguments. 

Base classes are comma separated inside the parentheses. They must come after the generic arguments.
The parentheses may be omitted if this class has no bases.
Base classes must already exist prior to this classes declaration. 
The base classes must be valid types, meaning they can be generics which take a generic parameter of this class as an argument.

The body of a class must be comprised entirely of attributes, methods, and one or no constructors.

##### Attributes:

Any attributes of the class (excluding methods), are declared by the following syntax:

`attr foo: foo_type;`

They are assigned default values base on their type prior to the constructor being called, which are as follows:
* int: 0
* str: ""
* Any Object: null


##### Methods:

Methods of the class take `self`, which is an instance of the class, as an implicit first argument. They are declared as follows:

`method foo(baz: baz_type, bar: bar_type) -> foo_return_type { ... }`

Argument types and the return type must be specified. A variable number of arguments is not supported, nor are method specific generic parameters.
See functions for information about the body of methods.


##### Constructor:

Constructors for classes are what is called with the arguments in the `new` expression. They are declared similarly to methods:

`new(foo: foo_type)`

The return type must not be specified, but argument types must. Do not return anything in a constructor, only assign values to `self`.


#### Functions

Functions are declared the same as methods, but with `def` as the keyword instead of `method`:

`def fibo(n: int) -> int { ... }`

(Generic support in functions coming soon)
The body of a function (and method) must be entirely statements, which are similar to statements in other C-family languages. Therefore, they will only be skimmed.

##### Statements

* Variable declaration: `var var_name: var_type = value_expr;`
* If statement: `if (condition_expr) stmt`. There can be an optional else-clause following the statement: `else another_stmt`. The statement can be either a single statement, or a block.
* Block: `{ stmts }`. Blocks have their own scope for variables
* While statement: `while (cond) stmt`
* Return: `return expr;`
* Expression Statement: `expr;` These are void return calls and assignments.


##### Expressions
Calls, arithmetic, etc.
Notable:

* Casts: `obj as type` Downcasts are always safe, Upcasts are not safe at all and can cause a Seg fault if the obj cannot be cast
* Assignment is an expression
