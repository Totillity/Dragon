from typing import Dict, List

from dragon.common import ast, DragonError, cgen


class CompilingError(DragonError):
    pass


class Visitor:
    def visit(self, obj, *args, **kwargs):
        try:
            method = getattr(self, "visit_" + obj.__class__.__name__)
        except AttributeError:
            method = self.default

        return method(obj, *args, **kwargs)

    def default(self, obj, *args, **kwargs):
        raise AttributeError("No visitor for " + repr(obj))


class ClassType(cgen.DataType):
    def __init__(self, name: str, bases: List['ClassType']):
        self.typ = "struct " + name + "*"
        self.name = name
        self.bases = bases
        self.attrs: Dict[str, cgen.Type] = {}
        self.methods: Dict[str, cgen.FunctionType] = {}
        self.other: Dict[str, cgen.Type] = {}

        self.c_names: Dict[str, str] = {}

        self.struct = cgen.StructType(name)

    def get_name(self, obj: cgen.Expression, name: str):
        if name in self.c_names:
            return cgen.GetArrow(obj, self.c_names[name])
        else:
            for base in self.bases:
                try:
                    return base.get_name(cgen.GetArrow(obj, 'parent_' + base.name), name)
                except KeyError:
                    pass
            else:
                raise KeyError(name)

    @property
    def fields(self):
        fields = {}
        fields.update({'parent_'+base.name: base.struct for base in self.bases})
        fields.update(self.attrs)
        fields.update(self.methods)
        fields.update(self.other)
        return fields


def count_str():
    i = 0
    while True:
        yield str(i)
        i += 1


class Environment:
    def __init__(self):
        self.var_scopes: List[Dict[str, str]] = []
        self.type_scopes: List[Dict[str, cgen.Type]] = []
        self.scope_names: List[str] = []

        self.ids = count_str()

    def curr_scope(self):
        return self.scope_names[-1]

    def scope_depth(self):
        return len(self.scope_names)

    def new_scope(self, name: str):
        self.var_scopes.append({})
        self.type_scopes.append({})
        self.scope_names.append(name)

    def end_scope(self):
        self.var_scopes.pop()
        self.type_scopes.pop()
        self.scope_names.pop()

    def new_var(self, name: str, hidden=False, is_builtin=False):
        if hidden:
            if is_builtin:
                return
        else:
            if is_builtin:
                self.var_scopes[-1][name] = name
            else:
                self.var_scopes[-1][name] = '_'.join(self.scope_names + [name, next(self.ids)])
            return self.var_scopes[-1][name]

    def extend_vars(self, new_vars):
        for new_var in new_vars:
            self.new_var(new_var)

    def new_type(self, name: str, typ: cgen.Type):
        self.type_scopes[-1][name] = typ

    def get_var(self, name: str):
        for scope in reversed(self.var_scopes):
            if name in scope:
                return scope[name]

        raise KeyError(name)

    def get_type(self, name: str):
        for scope in reversed(self.type_scopes):
            if name in scope:
                return scope[name]

        raise KeyError(name)


class Compiler(Visitor):
    def __init__(self):
        self.names = Environment()

        self.main = None

    def visit_Program(self, node: ast.Program):
        self.names.new_scope("globals")

        self.names.new_var("printf", is_builtin=True)
        self.names.new_type("int", cgen.IntType())
        self.names.new_type("str", cgen.PointerType(cgen.CharType()))
        self.names.new_type("void", cgen.VoidType())

        # array = ClassType("Array", [])
        # array.c_names["length"] = "length"
        # # array.
        #
        # self.names.new_type("array", ClassType("Array", []))

        for top_level in node.top_level:
            if isinstance(top_level, ast.Function):
                pass
            elif isinstance(top_level, ast.Class):
                c_name = self.names.new_var("class_"+top_level.name)
                bases = [self.visit(base) for base in top_level.bases]

                self.names.new_type(top_level.name, ClassType(c_name, bases))
            else:
                raise NotImplementedError()

        top_levels = [cgen.Include("stdio.h"), cgen.Include("stdlib.h"), cgen.Include("dragon.h", angled=False), cgen.Include("list.h", angled=False)]

        for top_level in node.top_level:
            top_levels.extend(self.visit(top_level))

        main_func = cgen.Function("main", {}, cgen.IntType(), [cgen.Return(cgen.Call(cgen.GetVar(self.main), []))])
        top_levels.append(main_func)

        self.names.end_scope()

        program = cgen.Program(top_levels)
        return program

    def visit_Class(self, node: ast.Class):
        cls_type: ClassType = self.names.get_type(node.name)

        for cls_stmt in node.body:
            if isinstance(cls_stmt, ast.Attr):
                cls_type.attrs[cls_stmt.name] = self.visit(cls_stmt.type)
            elif isinstance(cls_stmt, ast.Method):
                cls_type.methods[cls_stmt.name] = cgen.PointerType(
                    cgen.FunctionType([cls_type] + [self.visit(arg) for arg in cls_stmt.args.values()], self.visit(cls_stmt.ret)))
            elif isinstance(cls_stmt, ast.Constructor):
                cls_type.other["new"] = cgen.PointerType(
                    cgen.FunctionType([self.visit(arg) for arg in cls_stmt.args.values()], cls_type))
            else:
                raise Exception(cls_stmt)

        others = []

        if "new" not in cls_type.other:
            constructor = cgen.Function("new_" + cls_type.name, {}, cls_type, [
                cgen.Declare(cls_type, "obj",
                             cgen.Call(cgen.GetVar("new_empty_" + cls_type.name), [])),
                cgen.Return(cgen.GetVar('obj'))
            ])
            cls_type.other["new"] = cgen.PointerType(cgen.FunctionType([], cls_type))
            cls_type.c_names["new"] = "new_" + cls_type.name
            others.append(constructor)

        self.names.new_scope(cls_type.name)

        for cls_stmt in node.body:
            others.extend(self.visit(cls_stmt, cls_type))

        self.names.end_scope()

        new_empty = cgen.Function("new_empty_" + cls_type.name, {}, cls_type, [
            cgen.Declare(cls_type, "obj",
                         cgen.Call(cgen.GetVar("malloc"), [cgen.SizeOf(cls_type.struct)])),
            *(
                cgen.ExprStmt(cgen.SetArrow(cgen.GetVar("obj"), attr_name, self.default_of(attr_type)))
                for attr_name, attr_type in cls_type.attrs.items()
            ),

            *(
                cgen.ExprStmt(
                    cgen.SetArrow(cgen.GetVar("obj"), method_name, cgen.GetVar(cls_type.c_names[method_name])))
                for method_name, method_type in cls_type.methods.items()
            ),
            cgen.Return(cgen.GetVar("obj"))
        ])

        others.append(new_empty)

        return [cgen.Struct(cls_type.name, cls_type.fields), *others]

    # noinspection PyMethodMayBeStatic
    def visit_Attr(self, node: ast.Attr, cls_type: ClassType):
        cls_type.c_names[node.name] = node.name
        return []

    def visit_Method(self, node: ast.Method, cls_type: ClassType):
        c_name = self.names.new_var(node.name)
        cls_type.c_names[node.name] = c_name

        self.names.new_scope(node.name)

        ret = self.visit(node.ret)
        # args = {'self': cls_type}
        args = {'self': cls_type}
        self.names.new_var("self", is_builtin=True)
        args.update({self.names.new_var(name): self.visit(arg) for name, arg in node.args.items()})

        # self.names.extend_vars(args)
        body = [self.visit(stmt) for stmt in node.body]

        self.names.end_scope()

        # print(args)
        return [cgen.Function(c_name, args, ret, body)]

    def visit_Function(self, node: ast.Function):
        c_name = self.names.new_var(node.name)

        if self.names.scope_depth() == 1 and node.name == "main":
            self.main = c_name

        self.names.new_scope(node.name)

        ret = self.visit(node.ret)
        args = {self.names.new_var(name): self.visit(arg) for name, arg in node.args.items()}

        body = [self.visit(stmt) for stmt in node.body]

        self.names.end_scope()

        return [cgen.Function(c_name, args, ret, body)]

    def visit_Name(self, node: ast.Name):
        return self.names.get_type(node.name)

    @staticmethod
    def default_of(typ: cgen.Type):
        if isinstance(typ, cgen.PointerType) and isinstance(typ.pointee, cgen.CharType):
            return cgen.Constant(typ, "")
        elif isinstance(typ, cgen.IntType):
            return cgen.Constant(typ, 0)
        else:
            raise Exception(typ)

    def visit_VarStmt(self, node: ast.VarStmt):
        c_name = self.names.new_var(node.name)
        if node.val is None:
            val = None
        else:
            val = self.visit(node.val)
        return cgen.Declare(self.visit(node.typ), c_name, val)

    def visit_ReturnStmt(self, node: ast.ReturnStmt):
        if node.expr is None:
            # noinspection PyTypeChecker
            return cgen.Return(None)
        else:
            expr = self.visit(node.expr)
            return cgen.Return(expr)

    def visit_ExprStmt(self, node: ast.ExprStmt):
        expr = self.visit(node.expr)
        return cgen.ExprStmt(expr)

    def visit_GetVar(self, node: ast.GetVar):
        return cgen.GetVar(self.names.get_var(node.var))

    def visit_SetVar(self, node: ast.SetVar):
        return cgen.SetVar(self.names.get_var(node.var), self.visit(node.val))

    def visit_Call(self, node: ast.Call):
        callee = self.visit(node.callee)
        args = [self.visit(arg) for arg in node.args]
        return cgen.Call(callee, args)

    def visit_GetAttr(self, node: ast.GetAttr):
        return cgen.GetArrow(self.visit(node.obj), node.attr)

    def visit_SetAttr(self, node: ast.SetAttr):
        return cgen.SetArrow(self.visit(node.obj), node.attr, self.visit(node.val))

    def visit_New(self, node: ast.New):
        cls: ClassType = self.visit(node.cls)
        return cgen.Call(cgen.GetVar("new_" + cls.name), [self.visit(arg) for arg in node.args])

    # noinspection PyMethodMayBeStatic
    def visit_Literal(self, node: ast.Literal):
        if node.type == "num":
            return cgen.Constant(int(node.val))
        elif node.type == "str":
            return cgen.Constant(node.val[1:-1])
        else:
            raise Exception(node.type)


def compile_drgn(tree):
    compiler = Compiler()
    program: cgen.Program = compiler.visit(tree)
    return program
