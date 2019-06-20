from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple

__all__ = ['Node',

           'Type', 'Name', 'GetName', 'Generic', ''
           
           'Expr', 'Call', 'Literal', 'GetVar', 'BinOp',
           'GetAttr', 'SetAttr', 'SetVar', 'Cast', 'Grouping', 'New', 'Unary',

           'Stmt', 'ReturnStmt', 'ExprStmt', 'VarStmt', 'Block', 'IfStmt', 'WhileStmt', 'DeleteStmt',

           'ClassStmt', 'Constructor', 'Attr', 'Method',

           'TopLevel', 'Function', 'Class', 'GenericClass', 'Import', 'OverloadedFunction', 'Overload',

           'Program', ]


@dataclass()
class Node:
    line: int = field(init=False)
    pos: (int, int) = field(init=False)
    meta: Dict[str, Any] = field(init=False)

    def place(self, line, line_pos):
        self.meta = {}
        has_line = hasattr(self, 'line')
        has_pos = hasattr(self, 'pos')
        if not (has_line or has_pos):
            self.line = line
            self.pos = line_pos
        elif has_line and has_pos:
            pass
        else:
            raise Exception(f"Only one of .line or .pos defined")


@dataclass()
class Type(Node):
    pass


@dataclass()
class Name(Type):
    name: str


@dataclass()
class GetName(Type):
    type: Type
    name: str


@dataclass()
class Generic(Type):
    type: Type
    args: List[Type]


@dataclass()
class Expr(Node):
    # ret_type: Type = field(init=False, default=None)
    pass


@dataclass()
class BinOp(Expr):
    left: Expr
    op: str
    right: Expr


@dataclass()
class Unary(Expr):
    op: str
    right: Expr


@dataclass()
class Call(Expr):
    callee: Expr
    args: List[Expr]


@dataclass()
class Cast(Expr):
    obj: Expr
    type: Type


@dataclass()
class New(Expr):
    cls: Type
    args: List[Expr]


@dataclass()
class Grouping(Expr):
    expr: Expr


@dataclass()
class GetVar(Expr):
    var: str


@dataclass()
class GetAttr(Expr):
    obj: Expr
    attr: str


@dataclass()
class Literal(Expr):
    type: str
    val: str


@dataclass()
class SetVar(Expr):
    var: str
    val: Expr


@dataclass()
class SetAttr(Expr):
    obj: Expr
    attr: str
    val: Expr


@dataclass()
class Stmt(Node):
    pass


@dataclass()
class Block(Stmt):
    stmts: List[Stmt]


@dataclass()
class IfStmt(Stmt):
    cond: Expr
    then_do: Stmt
    else_do: Stmt


@dataclass()
class WhileStmt(Stmt):
    cond: Expr
    body: Stmt


@dataclass()
class VarStmt(Stmt):
    name: str
    typ: Type
    val: Expr


@dataclass()
class DeleteStmt(Stmt):
    obj: Expr


@dataclass()
class ReturnStmt(Stmt):
    expr: Expr


@dataclass()
class ExprStmt(Stmt):
    expr: Expr


@dataclass()
class ClassStmt(Node):
    pass


@dataclass()
class Attr(ClassStmt):
    name: str
    type: Type


@dataclass()
class Method(ClassStmt):
    name: str
    args: Dict[str, Type]
    ret: Type
    body: List[Stmt]


@dataclass()
class Constructor(ClassStmt):
    args: Dict[str, Type]
    body: List[Stmt]


@dataclass()
class TopLevel(Node):
    pass


@dataclass()
class Class(TopLevel):
    name: str
    bases: List[Type]
    body: List[ClassStmt]


@dataclass()
class GenericClass(Class):
    type_vars: List[str]

    implements: List[Class] = field(default_factory=list)


@dataclass()
class Function(TopLevel):
    name: str
    args: Dict[str, Type]
    ret: Type
    body: List[Stmt]


@dataclass()
class Overload(Node):
    args: Dict[str, Type]
    ret: Type
    body: List[Stmt]


@dataclass()
class OverloadedFunction(TopLevel):
    name: str
    overloads: List[Overload]


@dataclass()
class Import(TopLevel):
    file: str


@dataclass()
class Program(Node):
    top_level: List[TopLevel]
