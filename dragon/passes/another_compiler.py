import os
import pathlib
from typing import Dict, Type

from dragon.common import ast, DragonError, cgen, Visitor
from dragon.passes.resolver import Resolver


class CompilingError(DragonError):
    pass


class Compiler(Visitor):
    def __init__(self):
        self.main_func = ''

    def visit_Program(self, node: ast.Program):
        c_files = pathlib.Path(os.path.realpath(__file__)).parent.parent / "std_files"

        dragon_h = str(c_files / "dragon.h")
        list_h = str(c_files / "list.h")

        top_levels = [cgen.Include("stdio.h"), cgen.Include("stdlib.h"), cgen.Include("stdbool.h"),
                      cgen.Include(dragon_h, angled=False), cgen.Include(list_h, angled=False)]

        for top_level in node.top_level:
            top_levels += self.visit(top_level)

        if not self.main_func:
            raise CompilingError("No main function", -1, (0, 0))

        top_levels.append(cgen.Function("main", {}, cgen.IntType(), [
            cgen.Return(cgen.Call(cgen.GetVar(self.main_func), []))
        ]))

        program = cgen.Program(top_levels)
        return program

    def default_of(self, type: cgen.Type):
        if isinstance(type, cgen.IntType):
            return cgen.Constant(0)
        elif (isinstance(type, cgen.PointerType) and isinstance(type.pointee, cgen.CharType)) or isinstance(type, cgen.StringType):
            return cgen.Constant("")
        else:
            return cgen.Constant(None)
            # raise Exception(type)

    def visit_GenericClass(self, node: ast.GenericClass):
        clses = []
        for implement in node.implements:
            clses += self.visit_Class(implement)
        return clses

    def visit_Class(self, node: ast.Class):
        cls_type: cgen.ClassType = node.meta["type"]
        has_constructor = node.meta["has_constructor"]

        cls_struct = cgen.Struct(node.meta["c_name"], {
            'self': cgen.VoidPointerType(),
            'up': cgen.VoidPointerType(),

            **{'parent_'+base.name: base.struct for base in cls_type.bases},

            **cls_type.attrs,
            **cls_type.methods,
        })

        cls_type.struct = cls_struct.struct_type

        new_empty = cgen.Function("new_empty_"+node.meta["c_name"], {}, cls_type, [
            cgen.Declare(cls_type, "obj", cgen.Call(cgen.GetVar("malloc"), [cgen.SizeOf(cls_struct.struct_type)])),
            cgen.ExprStmt(cgen.SetArrow(cgen.GetVar("obj"), "self", cgen.GetVar("obj"))),
            cgen.ExprStmt(cgen.SetArrow(cgen.GetVar("obj"), "up", cgen.GetVar("obj"))),

            *(
                cgen.ExprStmt(cgen.Call(cgen.GetVar("new_parent_"+base.name), [cgen.Ref(cgen.GetArrow(cgen.GetVar("obj"), 'parent_'+base.name)), cgen.GetVar('obj'), cgen.GetVar('obj')]))
                for base in cls_type.bases
            ),

            *(
                cgen.ExprStmt(cls_type.set_name_expr(cgen.Deref(cgen.GetVar('obj')), attr, self.default_of(attr_type)))
                for attr, attr_type in cls_type.all_attrs()
            ),

            *(
                cgen.ExprStmt(cls_type.set_name_expr(cgen.Deref(cgen.GetVar("obj")), method_name, cgen.GetVar(method_c_name)))
                for method_name, method_c_name in node.meta["all methods"].items()
            ),
            cgen.Return(cgen.GetVar('obj'))
        ])

        redirects = []
        for method_name, method_c_name in node.meta["inherited methods"].items():
            redirect_type: cgen.Type = cls_type.get_name(method_name)
            assert isinstance(redirect_type, cgen.PointerType), f"{redirect_type}"
            redirect_to: cgen.FunctionType = redirect_type.pointee

            args = {'_self': cgen.VoidPointerType()}
            args.update({"arg_"+str(i): arg_type for i, arg_type in enumerate(redirect_to.args[1:])})

            passed_args = [cgen.Ref(cls_type.cast_for_name_expr(cgen.Deref(cgen.GetVar('self')), method_name))]
            passed_args.extend(cgen.GetVar("arg_"+str(i)) for i, arg_type in enumerate(redirect_to.args[1:]))

            if isinstance(redirect_to.ret, cgen.VoidType):
                redirect = cgen.Function(method_c_name,
                                         args,
                                         redirect_to.ret, [
                                                cgen.Declare(cls_type, 'self', cgen.GetVar('_self')),
                                                cgen.ExprStmt(cgen.Call(cgen.GetVar(cls_type.get_c_name(method_name)),
                                                                        passed_args))
                                         ])
            else:
                redirect = cgen.Function(method_c_name,
                                         args,
                                         redirect_to.ret, [
                                             cgen.Declare(cls_type, 'self', cgen.GetVar('_self')),
                                             cgen.Return(cgen.Call(cgen.GetVar(cls_type.get_c_name(method_name)),
                                                                   passed_args))
                                         ])
            redirects.append(redirect)

        new_parent = cgen.Function("new_parent_"+node.meta["c_name"],
                                   {'parent_ptr': cls_type, 'child_ptr': cgen.VoidPointerType(), 'self_ptr': cgen.VoidPointerType()},
                                   cgen.VoidType(), [
            cgen.ExprStmt(cgen.SetArrow(cgen.GetVar("parent_ptr"), 'self', cgen.GetVar('self_ptr'))),
            cgen.ExprStmt(cgen.SetArrow(cgen.GetVar("parent_ptr"), 'up', cgen.GetVar("child_ptr"))),
            *(
                cgen.ExprStmt(cgen.Call(
                    cgen.Ref(cgen.GetVar("new_parent_"+base.name)),
                    [cgen.Ref(cgen.GetArrow(cgen.GetVar('parent_ptr'), 'parent_'+base.name)), cgen.GetVar('parent_ptr'), cgen.GetVar('self_ptr')]
                ))
                for base in cls_type.bases
            )
        ])

        body_stmt_items = []
        for body_stmt in node.body:
            body_stmt_items += self.visit(body_stmt)

        if not has_constructor:
            new = cgen.Function("new_"+node.meta["c_name"], {}, cls_type, [
                cgen.Declare(cls_type, "obj",
                             cgen.Call(cgen.GetVar("new_empty_" + cls_type.name), [])),
                cgen.Return(cgen.GetVar('obj'))
            ])
            cls_type.c_names["new"] = new.name
            body_stmt_items.append(new)

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
        body.append(cgen.Declare(node.meta["cls"], "self", cgen.Call(cgen.GetVar("new_empty_" + cls_type.name), [])))
        for stmt in node.body:
            body.append(self.visit(stmt))
        body.append(cgen.Return(cgen.GetVar("self")))
        return [cgen.Function(node.meta["c_name"], node.meta["args"], node.meta["cls"], body)]

    def visit_Function(self, node: ast.Function):
        if node.meta["is main"]:
            self.main_func = node.meta["c_name"]

        body = []
        for stmt in node.body:
            body.append(self.visit(stmt))
        return [cgen.Function(node.meta["c_name"], node.meta["c args"], node.meta["ret"], body)]

    def visit_IfStmt(self, node: ast.IfStmt):
        return cgen.If(self.visit(node.cond), self.visit(node.then_do), self.visit(node.else_do))

    def visit_WhileStmt(self, node: ast.WhileStmt):
        return cgen.While(self.visit(node.cond), self.visit(node.body))

    def visit_Block(self, node: ast.Block):
        return cgen.Block([self.visit(stmt) for stmt in node.stmts])

    def visit_VarStmt(self, node: ast.VarStmt):
        return cgen.Declare(node.meta["type"], node.meta["c_name"], self.coerce_node(node.val, node.meta["type"]))

    def visit_ExprStmt(self, node: ast.ExprStmt):
        return cgen.ExprStmt(self.visit(node.expr))

    def visit_ReturnStmt(self, node: ast.ReturnStmt):
        return cgen.Return(self.visit(node.expr))

    def visit_New(self, node: ast.New):
        return cgen.Call(cgen.GetVar(node.meta["cls"].c_names["new"]), [self.visit(arg) for arg in node.args])

    @classmethod
    def coerce_expr(cls, expr: cgen.Expression, from_type: cgen.Type, to_type: cgen.Type, node):
        if isinstance(from_type, cgen.ClassType) and isinstance(to_type, cgen.ClassType):
            if from_type is to_type:
                return expr
            else:

                return cgen.Ref(from_type.cast_expr(cgen.Deref(expr), to_type))
        else:
            if isinstance(from_type, to_type.__class__):
                return expr
            primitives: Dict[Type[cgen.Type], cgen.ClassType] = {cgen.IntType: cgen.Integer,
                                                                 cgen.StringType: cgen.String}
            if isinstance(to_type, cgen.ClassType):
                try:
                    wrapper = primitives[type(from_type)]
                except KeyError:
                    raise Exception(from_type, to_type)
                else:
                    as_object = cgen.Call(cgen.GetVar("_new_"+wrapper.name), [expr])
                    return cgen.Ref(wrapper.cast_expr(cgen.Deref(as_object), to_type))
            else:
                raise CompilingError(f"Cannot coerce {from_type} to {to_type}", node.line, node.pos)

    def coerce_node(self, node: ast.Node, expected: cgen.Type):
        return self.coerce_expr(self.visit(node), node.meta["ret"], expected, node)

    def visit_Call(self, node: ast.Call):
        args = []
        if isinstance(node.callee, ast.GetAttr):
            obj = node.callee.obj
            args.append(cgen.GetArrow(self.visit(obj), 'self'))
            expected_args = node.meta["func"].pointee.args[1:]
        else:
            expected_args = node.meta["func"].pointee.args

        for arg_node, expected in zip(node.args, expected_args):
            arg = self.coerce_expr(self.visit(arg_node), arg_node.meta["ret"], expected, arg_node)
            args.append(arg)
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
            obj = self.visit(node.obj)
            from_type = node.obj.meta["ret"]
            if not isinstance(to_type, cgen.ClassType):
                # TODO: Error message
                raise Exception()
            path = to_type.path_to_parent(from_type)[1:]

            # obj = cgen.Deref(obj)

            for base in path:
                obj = cgen.Cast(cgen.GetArrow(obj, 'up'), base)

            # obj = cgen.Ref(obj)

            return obj

    def visit_Literal(self, node: ast.Literal):
        return cgen.Constant(node.meta["val"])

    def visit_Grouping(self, node: ast.Grouping):
        return self.visit(node.expr)


def compile_drgn(tree):
    resolver = Resolver()
    resolver.visit_Program(tree)
    compiler = Compiler()
    program: cgen.Program = compiler.visit(tree)
    return program
