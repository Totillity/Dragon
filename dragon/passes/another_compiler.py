import os
import pathlib
from typing import Dict, Type, List

from dragon.common import ast, DragonError, cgen, Visitor
from dragon.passes.resolver import Resolver


class CompilingError(DragonError):
    pass


class Compiler(Visitor):
    # TODO: and also weak refs
    def __init__(self):
        self.main_func = ''
        self.programs: List[cgen.Program] = []

    def visit_Program(self, node: ast.Program, path: pathlib.Path, is_main=False):
        c_files = pathlib.Path(os.path.realpath(__file__)).parent.parent / "std_files"

        dragon_h = str(c_files / "dragon.h")
        list_h = str(c_files / "list.h")

        top_levels = [
            cgen.Include(dragon_h, angled=False),
            cgen.Include(list_h, angled=False)
        ]

        for top_level in node.top_level:
            top_levels += self.visit(top_level, is_main)

        if is_main:
            if self.main_func == '':
                raise CompilingError("No main function", -1, (0, 0))

            top_levels.append(cgen.Function("main", {}, cgen.CInt, [
                cgen.StrStmt(f"return {self.main_func}();")
            ]))

        program = cgen.Program(top_levels, path)
        self.programs.append(program)
        return program

    @classmethod
    def default_of(cls, type: cgen.Type):
        if cgen.is_int(type):
            return cgen.Constant(0)
        else:
            return cgen.Constant(None)

    def visit_Import(self, node: ast.Import, is_main=False):
        program: ast.Program = node.meta["program"]
        self.visit_Program(program, node.meta["path"])
        path: pathlib.Path = node.meta["path"]
        return [cgen.Include(str(path.with_suffix('.h')), angled=False)]

    def visit_GenericClass(self, node: ast.GenericClass, is_main=False):
        clses = []
        for implement in node.implements:
            clses += self.visit_Class(implement)
        return clses

    @classmethod
    def new_empty(cls, cls_node: ast.Class, cls_type: cgen.ClassType):
        new_empty = cgen.Function("new_empty_" + cls_node.meta["c_name"], {}, cls_type, [
            cgen.Declare(cls_type, "obj", cgen.Call(cgen.GetVar("malloc"), [cgen.SizeOf(cls_type.struct)])),
            cgen.StrStmt(f"obj->meta.self = obj;\n"
                         f"obj->meta.up = obj;\n"
                         f"obj->meta.ref_count = 0;\n"
                         f"obj->meta.ref_ptr = &(obj->meta.ref_count);\n"
                         f"obj->meta.del = del_{cls_node.meta['c_name']};"),
            *(
                cgen.StrStmt(f"new_parent_{base.name}(&obj->parent_{base.name}, obj, obj);")
                for base in cls_type.bases
            ),

            *(
                cgen.ExprStmt(cls_type.set_name_expr(cgen.Deref(cgen.GetVar('obj')), attr, cls.default_of(attr_type)))
                for attr, attr_type in cls_type.all_attrs()
            ),

            *(
                cgen.ExprStmt(
                    cls_type.set_name_expr(cgen.Deref(cgen.GetVar("obj")), method_name, cgen.GetVar(method_c_name)))
                for method_name, method_c_name in cls_node.meta["all methods"].items()
            ),
            cgen.Return(cgen.GetVar('obj'))
        ])
        return new_empty

    @classmethod
    def new_parent(cls, cls_node: ast.Class, cls_type: cgen.ClassType):
        new_parent = cgen.Function(
            "new_parent_" + cls_node.meta["c_name"],
            {'parent_ptr': cls_type, 'child_ptr': cgen.VoidPtr, 'self_ptr': cgen.VoidPtr},
            cgen.Void, [
                cgen.StrStmt("parent_ptr->meta.self = self_ptr;\n"
                             "parent_ptr->meta.up = child_ptr;"),
                *(
                    cgen.StrStmt(f"new_parent_{base.name}(&parent_ptr->parent_{base.name}, parent_ptr, self_ptr);")
                    for base in cls_type.bases
                )
            ]
        )
        return new_parent

    @classmethod
    def redirect(cls, cls_type: cgen.ClassType, name: str, func_name: str):
        redirect_type: cgen.PointerType = cls_type.get_name(name)
        assert cgen.is_func_ptr(redirect_type)
        redirect_to: cgen.FunctionType = redirect_type.pointee

        args = {'_self': cgen.VoidPtr, **{f"arg_{i}": arg_type for i, arg_type in enumerate(redirect_to.args[1:])}}

        passed = [cgen.Ref(cls_type.cast_for_name_expr(cgen.Deref(cgen.GetVar('self')), name))] + \
                 [cgen.GetVar(f"arg_{i}") for i, arg_type in enumerate(redirect_to.args[1:])]

        to_func = cgen.GetVar(cls_type.get_func_name(name))

        is_ret = not cgen.is_void(redirect_to.ret)
        redirect = cgen.Function(func_name, args, redirect_to.ret, [
            cgen.StrStmt(f"{cls_type} self = _self;"),
            (cgen.Return if is_ret else cgen.ExprStmt)(cgen.Call(to_func, passed))
        ]
                                 )
        return redirect

    def visit_Class(self, node: ast.Class, is_main=False):
        # TODO refactor this?

        cls_type: cgen.ClassType = node.meta["type"]
        has_constructor = node.meta["has_constructor"]
        has_destructor = False  # TODO: node.meta["has destructor"]

        cls_struct = cgen.Struct(node.meta["c_name"], {
            'meta': cgen.StructType("BaseObject"),

            **{'parent_' + base.name: base.struct for base in cls_type.bases},

            **cls_type.attrs,
            **cls_type.methods,
        })
        cls_type.struct = cls_struct.struct_type

        new_empty = self.new_empty(node, cls_type)

        redirects = []
        for method_name, method_c_name in node.meta["inherited methods"].items():
            redirect = self.redirect(cls_type, method_name, method_c_name)
            redirects.append(redirect)

        new_parent = self.new_parent(node, cls_type)

        body_stmt_items = []
        for body_stmt in node.body:
            body_stmt_items += self.visit(body_stmt)

        if not has_constructor:
            new = cgen.Function("new_" + node.meta["c_name"], {}, cls_type, [
                cgen.StrStmt(f"{cls_type.with_name('obj')} = new_empty_{cls_type.name}();\n"
                             f"return obj;")
            ])
            cls_type.func_names["new"] = new.name
            body_stmt_items.append(new)

        if not has_destructor:
            del_ = cgen.Function("del_" + node.meta["c_name"], {"obj": cgen.VoidPtr}, cgen.Void, [
                cgen.StrStmt(f"{cls_type} self = obj;"),
                cgen.dec_refs(cgen.StrExpr(f"self->{attr}")
                              for attr, typ in cls_type.attrs.items() if cgen.is_cls(typ)),
                cgen.ExprStmt(cgen.Call(cgen.GetVar("free"), [cgen.GetVar("self")]))
            ])
            cls_type.func_names["del"] = del_.name
            body_stmt_items.append(del_)

        return [cls_struct, new_empty, new_parent] + redirects + body_stmt_items

    def visit_Attr(self, node: ast.Attr):
        return []

    def visit_Method(self, node: ast.Method):
        body = []
        body.append(cgen.Declare(node.meta["cls"], "self", cgen.Cast(cgen.GetVar("_self"), node.meta["cls"])))
        for stmt in node.body:
            body.append(self.visit(stmt))
        return [cgen.Function(node.meta["c_name"], node.meta["args"], node.meta["ret"], body)]

    def visit_Constructor(self, node: ast.Constructor):
        body = []
        cls_type = node.meta["cls"]
        body.append(cgen.Declare(node.meta["cls"], "self", cgen.StrExpr(f"new_empty_{cls_type.name}()")))

        for stmt in node.body:
            body.append(self.visit(stmt))

        body.append(cgen.Return(cgen.GetVar("self")))

        return [cgen.Function(node.meta["c_name"], node.meta["args"], node.meta["cls"], body)]

    def visit_Function(self, node: ast.Function, is_main=None):
        if node.meta["is main"] and is_main:
            self.main_func = node.meta["c_name"]

        body = [self.visit(stmt) for stmt in node.body]

        return [cgen.Function(node.meta["c_name"], node.meta["c args"], node.meta["ret"], body)]

    def visit_IfStmt(self, node: ast.IfStmt):
        return cgen.If(self.visit(node.cond), self.visit(node.then_do), self.visit(node.else_do))

    def visit_WhileStmt(self, node: ast.WhileStmt):
        return cgen.While(self.visit(node.cond), self.visit(node.body))

    def visit_Block(self, node: ast.Block):
        return cgen.Block([self.visit(stmt) for stmt in node.stmts])

    def visit_VarStmt(self, node: ast.VarStmt):
        val = self.coerce_node(node.val, node.meta["type"])
        if cgen.is_cls(node.val.meta["ret"]):
            val = cgen.inc_ref(val)
        return cgen.Declare(node.meta["type"], node.meta["c_name"], val)

    def visit_ExprStmt(self, node: ast.ExprStmt):
        return cgen.ExprStmt(self.visit(node.expr))

    def visit_ReturnStmt(self, node: ast.ReturnStmt):
        to_delete: Dict[str, str] = node.meta["to delete"]
        dels = cgen.dec_refs(cgen.GetVar(c_name) for c_name in to_delete.values())
        return cgen.UnscopedBlock([dels, cgen.Return(self.visit(node.expr))])

    def visit_New(self, node: ast.New):
        return cgen.Call(cgen.GetVar(node.meta["cls"].c_names["new"]), [self.visit(arg) for arg in node.args])

    @classmethod
    def coerce_expr(cls, expr: cgen.Expression, from_type: cgen.Type, to_type: cgen.Type, node):
        if from_type is to_type:
            return expr

        if cgen.is_cls(from_type) and cgen.is_cls(to_type):
            # noinspection PyUnresolvedReferences
            return cgen.Ref(from_type.cast_expr(cgen.Deref(expr), to_type))
        else:
            if cgen.is_cls(to_type):
                if cgen.is_int(from_type):
                    as_object = cgen.Call(cgen.GetVar("_new_Integer"), [expr])
                    return cgen.Ref(cgen.Integer.cast_expr(cgen.Deref(as_object), to_type))
                else:
                    raise Exception(from_type, to_type)
            else:
                raise CompilingError(f"Cannot coerce {from_type} to {to_type}", node.line, node.pos)

    def coerce_node(self, node: ast.Node, expected: cgen.Type):
        return self.coerce_expr(self.visit(node), node.meta["ret"], expected, node)

    def visit_Call(self, node: ast.Call):
        args = []
        if isinstance(node.callee, ast.GetAttr):
            obj = node.callee.obj
            args.append(cgen.StrExpr(f"{self.visit(obj)}->meta.self"))
            expected_args = node.meta["func"].pointee.args[1:]
        else:
            expected_args = node.meta["func"].pointee.args

        args += [self.coerce_node(arg_node, expected) for arg_node, expected in zip(node.args, expected_args)]

        return cgen.Call(self.visit(node.callee), args)

    def visit_GetVar(self, node: ast.GetVar):
        return cgen.GetVar(node.meta["c_name"])

    def visit_SetVar(self, node: ast.SetVar):
        return cgen.SetVar(node.meta["c_name"], self.coerce_node(node.val, node.meta["ret"]))

    def visit_GetAttr(self, node: ast.GetAttr):
        cls: cgen.ClassType = node.obj.meta["ret"]
        return cls.get_name_expr(cgen.Deref(self.visit(node.obj)), node.attr)

    def visit_SetAttr(self, node: ast.SetAttr):
        cls: cgen.ClassType = node.obj.meta["ret"]

        expected = cls.get_name(node.attr)
        coerced = self.coerce_node(node.val, expected)

        if cgen.is_cls(expected):
            return cls.set_name_expr(cgen.Deref(self.visit(node.obj)), node.attr,
                                     cgen.inc_ref(coerced))
        else:
            return cls.set_name_expr(cgen.Deref(self.visit(node.obj)), node.attr, coerced)

    def visit_BinOp(self, node: ast.BinOp):
        return cgen.BinOp(self.visit(node.left), node.op, self.visit(node.right))

    def visit_Cast(self, node: ast.Cast):
        try:
            return self.coerce_node(node.obj, node.meta["ret"])
        except KeyError:
            # now force an upcast by calling up enough times to cast to the correct type,
            # but this will cause an error if the actual type is incorrect
            to_type = node.meta["ret"]
            from_type = node.obj.meta["ret"]
            obj = self.visit(node.obj)

            if not cgen.is_cls(to_type):
                # TODO: Error message
                raise Exception()

            path = to_type.path_to_parent(from_type)[1:]

            for base in path:
                obj = cgen.Cast(cgen.GetAttr(cgen.GetArrow(obj, "meta"), 'up'), base)

            return obj

    def visit_Literal(self, node: ast.Literal):
        if isinstance(node.meta["val"], str):
            val: str = node.meta["val"]
            esc_val = val.encode("utf-8").decode("unicode_escape")
            return cgen.StrExpr(f"_new_String(\"{val}\", {len(esc_val)})")

        return cgen.Constant(node.meta["val"])

    def visit_Grouping(self, node: ast.Grouping):
        return self.visit(node.expr)


def compile_drgn(tree, path: pathlib.Path) -> cgen.Unit:
    resolver = Resolver()
    resolver.visit_Program(tree)
    compiler = Compiler()
    compiler.visit_Program(tree, path, is_main=True)
    unit = cgen.Unit(compiler.programs)
    return unit
