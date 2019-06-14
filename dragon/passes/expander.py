from typing import List, Dict

from dragon.common import ast, Visitor


class Expander(Visitor):
    def __init__(self):
        pass

    def visit_Program(self, node: ast.Program):
        for top_level in node.top_level:
            self.visit(top_level)

    def visit_Class(self, node: ast.Class):
        for base in node.bases:
            self.visit(base)

        for body_stmt in node.body:
            self.visit(body_stmt)

    def visit_Attr(self, node: ast.Attr):
        self.visit(node.type)

    def visit_Method(self, node: ast.Method):
        self.visit(node.ret)
        for arg, type in node.args.items():
            self.visit(type)

    def default(self, obj: ast.Node, *args, **kwargs):
        for attr_name in dir(obj):
            if isinstance(getattr(obj, attr_name), ast.Node):
                self.visit(obj)


def expand(tree: ast.Node) -> ast.Node:
    expander = Expander()
    expander.visit(tree)
    return tree
