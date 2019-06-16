from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import List, Dict, cast

from dragon.common import cgen, ast, DragonError, Visitor


class ResolvingError(DragonError):
    pass


@dataclass()
class VarMeta:
    c_name: str
    type: cgen.Type


class Environment:
    def __init__(self):
        self.vars: List[Dict[str, VarMeta]] = []
        self.types: List[Dict[str, cgen.Type]] = []

        self.count = itertools.count()

    def next(self, name: str):
        return name + "_" + str(next(self.count))

    def new_scope(self, names: Dict[str, cgen.Type] = None):
        if names is None:
            names = {}
        else:
            names = {name: VarMeta(self.next(name), type) for name, type in names.items()}

        self.vars.append(names)
        self.types.append({})

    def end_scope(self):
        self.types.pop()
        return self.vars.pop()

    def new_var(self, var: str, type: cgen.Type, builtin=False, c_name=None) -> str:
        if builtin:
            if c_name is None:
                c_name = var
        else:
            c_name = self.next(var)
        self.vars[-1][var] = VarMeta(c_name, type)
        return c_name

    def extend_vars(self, vars: Dict[str, cgen.Type], builtin=False):
        return [self.new_var(var, type, builtin) for var, type in vars.items()]

    def get_var(self, var: str) -> VarMeta:
        for scope in self.vars:
            if var in scope:
                return scope[var]
        raise KeyError(var)

    def new_type(self, name: str, type: cgen.Type):
        self.types[-1][name] = type

    def get_type(self, name: str) -> cgen.Type:
        for scope in self.types:
            if name in scope:
                return scope[name]
        raise KeyError(name)


def inherited_methods(cls_type: cgen.ClassType):
    for base in cls_type.bases:
        yield from base.all_methods()


class Resolver(Visitor):
    def __init__(self):
        self.names = Environment()

    def visit_Name(self, node: ast.Name):
        type = self.names.get_type(node.name)
        node.meta["type"] = type
        return type

    def visit_Generic(self, node: ast.Generic):
        type: cgen.GenericClassType = self.visit(node.type)
        args: List[cgen.ClassType] = [self.visit(arg) for arg in node.args]

        if not isinstance(type, cgen.GenericClassType):
            raise ResolvingError(f"Generic type must be a generic class", node.type.line, node.type.pos)

        # TODO: check type of args

        arg_names = tuple(arg.name for arg in args)
        try:
            generic = type.generics[arg_names]
            return generic
        except KeyError:
            gen_cls_node: ast.GenericClass = type.node
            cls_name = self.names.next(gen_cls_node.name + '__' + '_'.join(arg_names))
            cls_node = ast.Class(cls_name, gen_cls_node.bases, gen_cls_node.body)
            cls_node.place(gen_cls_node.line, gen_cls_node.pos)

            self.names.new_scope()
            for name, arg in zip(type.type_vars, args):
                self.names.new_type(name, arg)

            bases = [self.visit(base) for base in cls_node.bases]
            c_name = cls_name
            cls_type = cgen.ClassType(c_name, bases)
            cls_node.meta["type"] = cls_type
            cls_node.meta["c_name"] = c_name

            self.visit_Class(cls_node)
            self.names.end_scope()

            gen_cls_node.implements.append(cls_node)
            type.generics[arg_names] = cls_type

            return cls_type

    def visit_Program(self, node: ast.Program):
        self.names.new_scope()

        self.names.new_type("int", cgen.IntType())
        self.names.new_type("str", cgen.StringType())
        self.names.new_type("void", cgen.VoidType())
        self.names.new_type("Object", cgen.Object)
        self.names.new_type("Integer", cgen.Integer)
        self.names.new_type("String", cgen.String)

        self.names.new_var("print", cgen.PointerType(cgen.FunctionType([cgen.Object], cgen.VoidType())), builtin=True)
        self.names.new_var("clock", cgen.PointerType(cgen.FunctionType([], cgen.IntType())), builtin=True,
                           c_name='dragon_clock')

        for top_level in node.top_level:
            if isinstance(top_level, ast.Function):
                type = cgen.PointerType(cgen.FunctionType([self.visit(arg)
                                                           for _, arg
                                                           in top_level.args.items()], self.visit(top_level.ret)))
                c_name = self.names.new_var(top_level.name, type)
                top_level.meta["type"] = type
                top_level.meta["c_name"] = c_name
                top_level.meta["args"] = {arg_name: arg_type
                                          for arg_name, arg_type
                                          in zip(top_level.args.keys(), cast(cgen.FunctionType, type.pointee).args)}
                # noinspection PyUnresolvedReferences
                top_level.meta["ret"] = type.pointee.ret
            elif isinstance(top_level, ast.GenericClass):
                c_name = self.names.next(top_level.name)
                type = cgen.GenericClassType(c_name, top_level.type_vars, top_level)
                self.names.new_type(top_level.name, type)
                top_level.meta["type"] = type
                top_level.meta["c_name"] = c_name
            elif isinstance(top_level, ast.Class):
                bases = [self.visit(base) for base in top_level.bases]
                c_name = self.names.next(top_level.name)
                type = cgen.ClassType(c_name, bases)
                self.names.new_type(top_level.name, type)
                top_level.meta["type"] = type
                top_level.meta["c_name"] = c_name
            else:
                raise Exception(top_level)

        for top_level in node.top_level:
            self.visit(top_level)

    def visit_GenericClass(self, node: ast.GenericClass):
        pass

    def visit_Class(self, node: ast.Class):
        cls_type: cgen.ClassType = node.meta["type"]
        node.meta["has_constructor"] = False

        if len(node.bases) == 0:
            cls_type.bases = [cgen.Object]

        for body_stmt in node.body:
            if isinstance(body_stmt, ast.Attr):
                type = self.visit(body_stmt.type)

                cls_type.attrs[body_stmt.name] = type

                body_stmt.meta["type"] = type
            elif isinstance(body_stmt, ast.Method):
                args = [cgen.VoidPointerType()]
                args.extend(self.visit(arg) for arg in body_stmt.args.values())
                ret = self.visit(body_stmt.ret)

                type = cgen.PointerType(cgen.FunctionType(args, ret))

                c_name = self.names.next(body_stmt.name)

                cls_type.methods[body_stmt.name] = type
                cls_type.c_names[body_stmt.name] = c_name

                body_stmt.meta["cls"] = cls_type
                body_stmt.meta["type"] = type
                body_stmt.meta["c_name"] = c_name
                body_stmt.meta["other args"] = {arg_name: arg_type
                                                for arg_name, arg_type
                                                in zip(body_stmt.args.keys(), args[1:])}
                body_stmt.meta["ret"] = ret
            elif isinstance(body_stmt, ast.Constructor):
                node.meta["has_constructor"] = True
                args = [self.visit(arg) for arg in body_stmt.args.values()]
                ret = cls_type

                type = cgen.PointerType(cgen.FunctionType(args, ret))

                c_name = self.names.next(node.name + "_new")

                cls_type.other["new"] = type
                cls_type.c_names["new"] = c_name

                body_stmt.meta["cls"] = cls_type
                body_stmt.meta["type"] = type
                body_stmt.meta["c_name"] = c_name
                body_stmt.meta["other args"] = {arg_name: arg_type
                                                for arg_name, arg_type
                                                in zip(body_stmt.args.keys(), args)}
                body_stmt.meta["ret"] = ret
            else:
                raise Exception(body_stmt)

        node.meta["inherited methods"] = {}
        node.meta["all methods"] = {}
        for method in cls_type.methods.keys():
            node.meta["all methods"][method] = cls_type.c_names[method]

        for inherited in inherited_methods(cls_type):
            c_name = self.names.next(node.meta["c_name"]+"_redirect_"+inherited)
            node.meta["all methods"][inherited] = c_name
            node.meta["inherited methods"][inherited] = c_name

        for body_stmt in node.body:
            self.visit(body_stmt)

    def visit_Attr(self, node: ast.Attr):
        pass

    def visit_Method(self, node: ast.Method):
        type = node.meta["type"]
        self.names.new_scope()
        self.names.new_var("_self", cgen.VoidPointerType(), builtin=True)
        self.names.new_var('self', node.meta["cls"], builtin=True)
        c_names = self.names.extend_vars(node.meta["other args"])
        # print(node.meta["other args"].items())
        node.meta["args"] = {'_self': cgen.VoidPointerType(), **dict(zip(c_names, node.meta["other args"].values()))}
        returns = []
        for stmt in node.body:
            returns.extend(self.visit(stmt))
        self.names.end_scope()

        # TODO: Return validation
        # for ret in returns:
        #     if ret != type.ret:
        #         raise ResolvingError(f"Expected return of {type.ret}, got a possible {ret}", node.line, node.pos)

    def visit_Constructor(self, node: ast.Constructor):
        type = node.meta["type"]
        self.names.new_scope()
        # self.names.new_var("_self", cgen.VoidPointerType(), builtin=True)
        self.names.new_var('self', node.meta["cls"], builtin=True)
        c_names = self.names.extend_vars(node.meta["other args"])

        node.meta["args"] = {**dict(zip(c_names, node.meta["other args"].values()))}

        for stmt in node.body:
            self.visit(stmt)
        self.names.end_scope()

    def visit_Function(self, node: ast.Function):
        if node.name == "main" and len(self.names.vars) == 1:
            node.meta["is main"] = True
        else:
            node.meta["is main"] = not True

        type = node.meta["type"]
        returns = []
        self.names.new_scope()

        c_names = self.names.extend_vars({arg: typ for arg, typ in node.meta["args"].items()})
        node.meta["c args"] = dict(zip(c_names, node.meta["args"].values()))

        for stmt in node.body:
            returns.extend(self.visit(stmt))
        self.names.end_scope()
        # TODO: Return validation

    def visit_New(self, node: ast.New):
        cls = self.visit(node.cls)
        node.meta["cls"] = cls
        node.meta["args"] = [self.visit(arg) for arg in node.args]
        node.meta["ret"] = cls
        return []

    def visit_IfStmt(self, node: ast.IfStmt):
        cond = self.visit(node.cond)
        returns = self.visit(node.then_do) + self.visit(node.else_do)
        return returns

    def visit_WhileStmt(self, node: ast.WhileStmt):
        cond = self.visit(node.cond)
        returns = self.visit(node.body)
        return returns

    def visit_Block(self, node: ast.Block):
        returns = []
        for stmt in node.stmts:
            returns.extend(self.visit(stmt))
        return returns

    def visit_VarStmt(self, node: ast.VarStmt):
        type = self.visit(node.typ)
        c_name = self.names.new_var(node.name, type)
        self.visit(node.val)
        node.meta["type"] = type
        node.meta["c_name"] = c_name
        return []

    def visit_ExprStmt(self, node: ast.ExprStmt):
        self.visit(node.expr)
        return []

    def visit_ReturnStmt(self, node: ast.ReturnStmt):
        return [self.visit(node.expr)]

    def visit_GetVar(self, node: ast.GetVar):
        data = self.names.get_var(node.var)
        node.meta["ret"] = data.type
        node.meta["c_name"] = data.c_name
        return data.type

    def visit_SetVar(self, node: ast.SetVar):
        data = self.names.get_var(node.var)
        self.visit(node.val)
        node.meta["ret"] = data.type
        node.meta["c_name"] = data.c_name

    def visit_GetAttr(self, node: ast.GetAttr):
        obj_type = self.visit(node.obj)
        if not isinstance(obj_type, cgen.ClassType):
            raise ResolvingError(f"Can only get attributes on objects, not {obj_type}", node.line, node.pos)
        else:
            try:
                type = obj_type.get_name(node.attr)
            except KeyError:
                raise ResolvingError(f"Class {obj_type} does not have the attribute {node.attr}", node.line, node.pos)

        node.meta["ret"] = type
        return type

    def visit_SetAttr(self, node: ast.SetAttr):
        # TODO: check if value is valid
        obj_type = self.visit(node.obj)
        if not isinstance(obj_type, cgen.ClassType):
            raise ResolvingError("Can only set attributes on objects", node.line, node.pos)
        else:
            try:
                type = obj_type.get_name(node.attr)
            except KeyError:
                raise ResolvingError(f"Class {obj_type} does not have the attribute {node.attr}", node.line, node.pos)

        self.visit(node.val)
        node.meta["ret"] = type
        return type

    def visit_Call(self, node: ast.Call):
        func_type = self.visit(node.callee)
        if not isinstance(func_type, cgen.PointerType) or not isinstance(func_type.pointee, cgen.FunctionType):
            raise ResolvingError(f"Callee must be a function, not a {func_type}", node.callee.line, node.callee.pos)

        node.meta["func"] = func_type
        node.meta["args"] = [self.visit(arg) for arg in node.args]
        node.meta["ret"] = func_type.pointee.ret
        return func_type.pointee.ret

    def visit_BinOp(self, node: ast.BinOp):
        def is_int(typ):
            return isinstance(typ, cgen.IntType)

        left = self.visit(node.left)
        right = self.visit(node.right)
        if node.op in ("+", "-", "*", "/"):
            if is_int(left) and is_int(right):
                ret = cgen.IntType()
            else:
                raise NotImplementedError(left, right, node.op)
        elif node.op in ("<", ">", ">=", "<=", "==", "!="):
            if is_int(left) and is_int(right):
                ret = cgen.BoolType()
            else:
                raise NotImplementedError(left, right, node.op)
        else:
            raise Exception(f"Unsupported operation: {node.op}")

        node.meta["ret"] = ret
        return ret

    def visit_Cast(self, node: ast.Cast):
        to_type = self.visit(node.type)
        self.visit(node.obj)
        node.meta["ret"] = to_type
        return to_type

    def visit_Literal(self, node: ast.Literal):
        if node.type == "num":
            node.meta["ret"] = cgen.IntType()
            node.meta["val"] = int(node.val)
            return cgen.IntType()
        elif node.type == "str":
            node.meta["ret"] = cgen.StringType()
            node.meta["val"] = node.val[1:-1]
            return cgen.StringType()
        else:
            raise Exception(node)

    def visit_Grouping(self, node: ast.Grouping):
        contents = self.visit(node.expr)
        node.meta["ret"] = contents
        return contents
