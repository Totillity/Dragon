from typing import List, Dict

from dragon.common import ast


class Visitor:
    def visit(self, obj, *args, **kwargs):
        try:
            method = getattr(self, "visit_" + obj.__class__.__name__)
        except AttributeError:
            method = self.default

        return method(obj, *args, **kwargs)

    def default(self, obj: ast.Node, *args, **kwargs):
        raise AttributeError(f"No visitor for {obj.__class__.__name__}")


class DragonType:
    pass


class IntType(DragonType):
    pass


class CharType(DragonType):
    pass


class FunctionType(DragonType):
    def __init__(self, args: List[DragonType], ret: DragonType):
        self.args = args
        self.ret = ret


class ClassType(DragonType):
    def __init__(self, name: str, bases: List[DragonType], cls: ast.Class):
        self.name = name
        self.bases = bases
        self.cls = cls

        self.attrs: Dict[str, DragonType] = {}
        self.methods: Dict[str, FunctionType] = {}
        self.other: Dict[str, DragonType] = {}


class Environment:
    def __init__(self):
        self.vars: List[Dict[str, DragonType]] = []
        self.types: List[Dict[str, DragonType]] = []

    def new_scope(self):
        self.vars.append({})
        self.types.append({})

    def end_scope(self):
        self.vars.pop()
        self.types.pop()

    def new_var(self, name: str, type: DragonType):
        self.vars[-1][name] = type

    def get_var(self, name: str):
        for scope in reversed(self.vars):
            if name in scope:
                return scope[name]

        raise KeyError(name)

    def new_type(self, name: str, type: DragonType):
        self.types[-1][name] = type

    def get_type(self, name: str):
        for scope in reversed(self.types):
            if name in scope:
                return scope[name]

        raise KeyError(name)


class Expander(Visitor):
    def __init__(self):
        self.names = Environment()

    def visit_Program(self, node: ast.Program):
        for top_level in node.top_level:
            pass

        for top_level in node.top_level:
            self.visit(top_level)

    def visit_Class(self, node: ast.Class):
        cls_type = ClassType(node.name, [], node)
        self.names.new_type(node.name, cls_type)
        bases = [self.visit(base) for base in node.bases]
        cls_type.bases = bases


    def default(self, obj: ast.Node, *args, **kwargs):
        for attr_name in dir(obj):
            if isinstance(getattr(obj, attr_name), ast.Node):
                self.visit(obj)


def expand(tree: ast.Node) -> ast.Node:
    expander = Expander()
    expander.visit(tree)
    return tree
