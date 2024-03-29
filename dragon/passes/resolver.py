from __future__ import annotations

import itertools
import pathlib
from dataclasses import dataclass
from typing import List, Dict, Tuple

from dragon.common import cgen, ast, DragonError, Visitor, MutableDict
from . import parser, scanner


class ResolvingError(DragonError):
    pass


@dataclass()
class VarMeta:
    c_name: str
    type: cgen.Type


class Module:
    def __init__(self, env: Environment):
        # only copy the globals, not the builtins such as Integer
        # so only the first layer of vars and types
        self.vars = env.vars.copy()
        self.types = env.types.copy()
        # TODO: Copy modules too?


class Environment:
    def __init__(self, vars: Dict[str, cgen.Type], types: Dict[str, cgen.Type], name: str = None,
                 parent: 'Environment' = None):
        self.vars: Dict[str, VarMeta] = {var: VarMeta(var, typ) for var, typ in vars.items()}
        self.types: Dict[str, cgen.Type] = types
        self.modules: Dict[str, Module] = {}

        self.parent = parent
        if parent is None:
            self.count = itertools.count()
        else:
            self.count = parent.count

        if name is None:
            self.name = self.next("scope")
        else:
            self.name = name

    def next(self, name: str):
        return name + "_" + str(next(self.count))

    def new_var(self, name: str, type: cgen.Type, builtin=False, c_name=''):
        if builtin:
            if c_name:
                self.vars[name] = VarMeta(c_name, type)
            else:
                self.vars[name] = VarMeta(name, type)
        else:
            self.vars[name] = VarMeta(self.next(name), type)
        return self.vars[name].c_name

    def extend_vars(self, names: Dict[str, cgen.Type], builtin=False, c_names=None):
        if c_names is None:
            c_names = itertools.repeat(None)
        else:
            if len(c_names) != len(names):
                raise Exception()
        return [self.new_var(name, type, builtin, c_name) for (name, type), c_name in zip(names.items(), c_names)]

    def new_type(self, name: str, type: cgen.Type):
        self.types[name] = type

    def new_scope(self, name: str = None) -> Tuple[Environment, Environment]:
        return self, Environment({}, {}, name, parent=self)

    def get_var(self, name: str) -> VarMeta:
        if name in self.vars:
            return self.vars[name]
        else:
            if self.parent:
                return self.parent.get_var(name)
            else:
                raise KeyError(name)

    def get_type(self, name: str) -> cgen.Type:
        if name in self.types:
            return self.types[name]
        else:
            if self.parent:
                return self.parent.get_type(name)
            else:
                raise KeyError(name)

    def get_module(self, name: str) -> Module:
        if name in self.modules:
            return self.modules[name]
        else:
            if self.parent:
                return self.parent.get_module(name)
            else:
                raise KeyError(name)

    def func_vars(self) -> Dict[str, VarMeta]:
        def add_dict(d1, d2):
            d3 = d1.copy()
            d3.update(d2)
            return d3

        if self.name.startswith("func "):
            return add_dict(self.vars, {})
        else:
            return add_dict(self.parent.func_vars(), self.vars)


def inherited_methods(cls_type: cgen.ClassType):
    for base in cls_type.bases:
        yield from base.all_methods()


class Resolver(Visitor):
    def __init__(self):
        self.names: Environment = Environment(
            {
                "print": cgen.SingleFuncType([cgen.Object], cgen.Void, "print"),
                "exit": cgen.SingleFuncType([cgen.Int], cgen.Void, "exit"),
                "is_null": cgen.SingleFuncType([cgen.Object], cgen.Bool, "is_null"),
            },
            {
                "int": cgen.Int,
                "void": cgen.Void,
                "Object": cgen.Object,
                "Integer": cgen.Integer,
                "String": cgen.String,
                "_Array": cgen.C_Array,
            }
        )

        self.names.new_var("clock", cgen.SingleFuncType([], cgen.Int, "dragon_clock"),
                           builtin=True, c_name='dragon_clock')
        self.names.new_var("null", cgen.NullType(),
                           builtin=True, c_name='NULL')

        self.MODULE_MODE = False

    def visit_Name(self, node: ast.Name):
        if self.MODULE_MODE:
            return self.names.get_module(node.name)
        else:
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

            old_scope = self.names
            _, cls_scope = type.scope.new_scope()
            self.names: Environment = cls_scope

            for name, arg in zip(type.type_vars, args):
                self.names.new_type(name, arg)

            bases = [self.visit(base) for base in cls_node.bases]
            c_name = cls_name
            cls_type = cgen.ClassType(c_name, bases)
            cls_node.meta["type"] = cls_type
            cls_node.meta["c_name"] = c_name

            self.visit_Class(cls_node)

            self.names: Environment = old_scope

            gen_cls_node.implements.append(cls_node)
            type.generics[arg_names] = cls_type

            return cls_type

    def visit_GetName(self, node: ast.GetName):
        if self.MODULE_MODE:
            pass
        else:
            self.MODULE_MODE = True
            module: Module = self.visit(node.type)
            self.MODULE_MODE = False
            return module.types[node.name]

    def visit_Program(self, node: ast.Program):
        modules_wide, new_scope = self.names.new_scope("globals")
        self.names: Environment = new_scope

        for top_level in node.top_level:
            if isinstance(top_level, ast.Function):
                c_name = self.names.next(top_level.name)
                type = cgen.SingleFuncType([self.visit(arg)
                                            for _, arg
                                            in top_level.args.items()], self.visit(top_level.ret), c_name)
                self.names.new_var(top_level.name, type, builtin=True, c_name=c_name)
                top_level.meta["type"] = type
                top_level.meta["c_name"] = c_name
                top_level.meta["args"] = {arg_name: arg_type
                                          for arg_name, arg_type
                                          in zip(top_level.args.keys(), type.args)}
                # noinspection PyUnresolvedReferences
                top_level.meta["ret"] = type.ret
            elif isinstance(top_level, ast.OverloadedFunction):
                overloads = MutableDict([])
                for n, overload in enumerate(top_level.overloads):
                    overload_type = ({arg: self.visit(typ) for arg, typ in overload.args.items()},
                                     self.visit(overload.ret))
                    c_name = self.names.next(top_level.name + "_" + str(n))
                    overloads[overload_type] = c_name
                    overload.meta["c_name"] = c_name
                    overload.meta["n"] = n
                    overload.meta["args"] = overload_type[0]
                    overload.meta["ret"] = overload_type[1]
                type = cgen.OverloadedFuncType(overloads)
                self.names.new_var(top_level.name, type)
                top_level.meta["type"] = type
                top_level.meta["overloads"] = overloads

            elif isinstance(top_level, ast.GenericClass):
                c_name = self.names.next(top_level.name)
                type = cgen.GenericClassType(c_name, top_level.type_vars, top_level, self.names)
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
            elif isinstance(top_level, ast.Import):
                this_scope = self.names
                self.names: Environment = modules_wide

                file_path = pathlib.Path(top_level.file)
                with open(file_path, "r") as file_obj:
                    file = file_obj.read()
                parsed = parser.parse(scanner.scan(file))
                module_scope = self.visit_Program(parsed)

                self.names: Environment = this_scope
                module = Module(module_scope)
                self.names.modules[file_path.with_suffix('').name] = module
                top_level.meta["module"] = module
                top_level.meta["path"] = file_path
                top_level.meta["program"] = parsed
            else:
                raise Exception(top_level)

        for top_level in node.top_level:
            self.visit(top_level)

        curr_scope = self.names
        self.names = modules_wide
        return curr_scope

    def visit_Import(self, node: ast.Import):
        pass

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
                args = [cgen.VoidPtr]
                args.extend(self.visit(arg) for arg in body_stmt.args.values())
                ret = self.visit(body_stmt.ret)

                c_name = self.names.next(body_stmt.name)
                type = cgen.SingleFuncType(args, ret, c_name)

                if not cls_type.has_name(body_stmt.name):
                    cls_type.methods[body_stmt.name] = type
                cls_type.func_names[body_stmt.name] = c_name

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

                c_name = self.names.next(node.name + "_new")
                type = cgen.SingleFuncType(args, ret, c_name)

                cls_type.other["new"] = type
                cls_type.func_names["new"] = c_name

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

        for inherited in inherited_methods(cls_type):
            if inherited in cls_type.func_names:
                c_name = cls_type.func_names[inherited]
            else:
                c_name = self.names.next(node.meta["c_name"] + "_redirect_" + inherited)
                node.meta["inherited methods"][inherited] = c_name
            node.meta["all methods"][inherited] = c_name

        for method in cls_type.methods.keys():
            if method not in node.meta["inherited methods"]:
                node.meta["all methods"][method] = cls_type.func_names[method]

        for body_stmt in node.body:
            self.visit(body_stmt)

    def visit_Attr(self, node: ast.Attr):
        pass

    def visit_Method(self, node: ast.Method):
        type = node.meta["type"]

        old_scope, new_scope = self.names.new_scope(f"func {node.name}")
        self.names: Environment = new_scope

        self.names.new_var("_self", cgen.VoidPtr, builtin=True)
        self.names.new_var('self', node.meta["cls"], builtin=True)
        c_names = self.names.extend_vars(node.meta["other args"])
        node.meta["args"] = {'_self': cgen.VoidPtr, **dict(zip(c_names, node.meta["other args"].values()))}
        returns = []
        for stmt in node.body:
            returns.extend(self.visit(stmt))

        self.names: Environment = old_scope

        # TODO: Return validation
        # for ret in returns:
        #     if ret != type.ret:
        #         raise ResolvingError(f"Expected return of {type.ret}, got a possible {ret}", node.line, node.pos)

    def visit_Constructor(self, node: ast.Constructor):
        type = node.meta["type"]

        old_scope, new_scope = self.names.new_scope("func new")
        self.names: Environment = new_scope

        self.names.new_var('self', node.meta["cls"], builtin=True)
        c_names = self.names.extend_vars(node.meta["other args"])

        node.meta["args"] = dict(zip(c_names, node.meta["other args"].values()))

        for stmt in node.body:
            self.visit(stmt)

        self.names: Environment = old_scope

    def visit_Function(self, node: ast.Function):
        if node.name == "main" and self.names.name == "globals":
            node.meta["is main"] = True
        else:
            node.meta["is main"] = not True

        type = node.meta["type"]
        returns = []

        old_scope, new_scope = self.names.new_scope(f"func {node.name}")
        self.names: Environment = new_scope

        c_names = self.names.extend_vars(node.meta["args"])
        node.meta["c args"] = dict(zip(c_names, node.meta["args"].values()))

        for stmt in node.body:
            returns.extend(self.visit(stmt))

        self.names: Environment = old_scope
        # TODO: Return validation

    def visit_OverloadedFunction(self, node: ast.OverloadedFunction):
        type = node.meta["type"]
        for overload in node.overloads:
            returns = []

            old_scope, new_scope = self.names.new_scope(f"func {overload.meta['c_name']}")
            self.names: Environment = new_scope

            c_names = self.names.extend_vars(overload.meta["args"])
            overload.meta["c args"] = dict(zip(c_names, overload.meta["args"].values()))

            for stmt in overload.body:
                returns.extend(self.visit(stmt))

            self.names: Environment = old_scope

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

    def visit_DeleteStmt(self, node: ast.DeleteStmt):
        self.visit(node.obj)
        node.meta["temp"] = self.names.next("temp")
        return []

    def visit_ExprStmt(self, node: ast.ExprStmt):
        self.visit(node.expr)
        return []

    def visit_ReturnStmt(self, node: ast.ReturnStmt):
        to_delete = {name: typ.c_name for name, typ in self.names.func_vars().items() if
                     cgen.is_cls(typ.type)}
        node.meta["to delete"] = to_delete
        return [self.visit(node.expr)]

    def visit_GetVar(self, node: ast.GetVar):
        try:
            data = self.names.get_var(node.var)
        except KeyError:
            raise ResolvingError(f"Name {node.var} is not defined", node.line, node.pos)
        node.meta["ret"] = data.type
        node.meta["c_name"] = data.c_name
        return data.type

    def visit_SetVar(self, node: ast.SetVar):
        try:
            data = self.names.get_var(node.var)
        except KeyError:
            raise ResolvingError(f"Name {node.var} is not defined", node.line,
                                 (node.pos[0], node.pos[0] + len(node.var)))
        self.visit(node.val)
        node.meta["ret"] = data.type
        node.meta["c_name"] = data.c_name

    def visit_GetAttr(self, node: ast.GetAttr):
        obj_type = self.visit(node.obj)
        if not cgen.is_cls(obj_type):
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
        if not cgen.is_cls(obj_type):
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
        passed = [self.visit(arg) for arg in node.args]
        func_type: cgen.FuncType = self.visit(node.callee)
        ret = func_type.ret_for(passed)
        if not cgen.is_func_ptr(func_type):
            raise ResolvingError(f"Callee must be a function, not a {func_type}", node.callee.line, node.callee.pos)

        node.meta["func"] = func_type
        node.meta["args"] = passed
        node.meta["ret"] = ret
        return ret

    def visit_BinOp(self, node: ast.BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if node.op in ("+", "-", "*", "/"):
            if cgen.is_int(left) and cgen.is_int(right):
                ret = cgen.Int
            else:
                raise NotImplementedError(left, right, node.op)
        elif node.op in ("<", ">", ">=", "<=", "==", "!="):
            if cgen.is_int(left) and cgen.is_int(right):
                ret = cgen.Bool
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
            node.meta["ret"] = cgen.Int
            node.meta["val"] = int(node.val)
            return cgen.Int
        elif node.type == "str":
            node.meta["ret"] = cgen.String
            node.meta["val"] = node.val[1:-1]
            return cgen.String
        else:
            raise Exception(node)

    def visit_Grouping(self, node: ast.Grouping):
        contents = self.visit(node.expr)
        node.meta["ret"] = contents
        return contents
