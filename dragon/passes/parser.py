from __future__ import annotations

from typing import List

from dragon.common.dragon_ast import *

from dragon.common import Token, DragonError

ORDER = "AFTER scanner"


class ParseError(DragonError):
    pass


class Stream:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens

    @property
    def curr(self) -> Token:
        return self.tokens[0]

    def advance(self):
        return Stream(self.tokens[1:]), self.tokens[0]

    def expect(self, typ: str):
        if self.curr.type == typ:
            return self.advance()
        else:
            raise self.error(f"Expected a '{typ}' token, got a '{self.curr.type}' token instead")

    def error(self, msg):
        raise ParseError(msg, self.curr.line, self.curr.pos)

    def is_empty(self):
        return len(self.tokens) == 0


def parsing_method(func):
    def _wrapper(stream: Stream):
        new_stream, node = func(stream)
        node.place(stream.curr.line, stream.curr.pos)
        return new_stream, node
    return _wrapper


class Parser:
    @staticmethod
    def parse_program(stream: Stream) -> Program:
        top_levels = []
        while not stream.is_empty():
            stream, top_level = Parser.parse_top_level(stream)
            top_levels.append(top_level)
        program = Program(top_levels)
        program.place(0, (0, 0))
        return program

    @staticmethod
    @parsing_method
    def parse_top_level(stream: Stream) -> (Stream, TopLevel):
        if stream.curr.type == 'class':
            return Parser.parse_class(stream)
        elif stream.curr.type == 'def':
            return Parser.parse_function(stream)
        else:
            raise stream.error(f"Cannot parse a top level statement from a '{stream.curr.type}' token")

    @staticmethod
    def arguments(start: str, stream: Stream, each, end: str) -> (Stream, List):
        args = []
        stream, _ = stream.expect(start)
        if stream.curr.type != end:
            while True:
                stream, arg = each(stream)
                args.append(arg)
                if stream.curr.type == ",":
                    stream, _ = stream.advance()
                else:
                    break
        stream, _ = stream.expect(end)
        return stream, args

    @staticmethod
    @parsing_method
    def parse_type(stream: Stream):
        return Parser.parse_generic(stream)

    @staticmethod
    @parsing_method
    def parse_generic(stream: Stream):
        stream, type = Parser.parse_dotted_name(stream)
        while stream.curr.type == "<":
            stream, args = Parser.arguments("<", stream, Parser.parse_type, ">")
            type = Generic(type, args)
        return stream, type

    @staticmethod
    @parsing_method
    def parse_dotted_name(stream: Stream):
        stream, type = Parser.parse_name(stream)
        while stream.curr.type == ".":
            stream, _ = stream.expect(".")
            stream, attr = stream.expect("ident")
            type = GetName(type, attr.text)
        return stream, type

    @staticmethod
    @parsing_method
    def parse_name(stream: Stream):
        stream, name = stream.expect("ident")
        type = Name(name.text)
        return stream, type

    @staticmethod
    @parsing_method
    def parse_function(stream: Stream):
        stream, _ = stream.expect("def")
        stream, name = stream.expect("ident")

        def parse_parameter(s: Stream):
            s, param_name = s.expect("ident")
            s, _ = s.expect(":")
            s, typ = Parser.parse_type(s)
            return s, (param_name.text, typ)

        stream, arg_tuples = Parser.arguments("(", stream, parse_parameter, ")")
        args = dict(arg_tuples)
        if stream.curr.type == "->":
            stream, _ = stream.expect("->")
            stream, ret = Parser.parse_type(stream)
        else:
            ret = None
        body = []
        stream, _ = stream.expect("{")
        while not stream.curr.type == "}":
            stream, stmt = Parser.parse_statement(stream)
            body.append(stmt)
        stream, _ = stream.expect("}")
        return stream, Function(name.text, args=args, ret=ret, body=body)

    @staticmethod
    @parsing_method
    def parse_class(stream: Stream) -> (Stream, Class):
        stream, _ = stream.expect("class")
        stream, name_token = stream.expect("ident")
        name = name_token.text
        if stream.curr.type == "(":
            stream, bases = Parser.arguments("(", stream, Parser.parse_type, ")")
        else:
            bases = []

        body = []
        stream, _ = stream.expect("{")
        while not stream.curr.type == "}":
            if stream.curr.type == "attr":
                stream, attr = Parser.parse_attr(stream)
                body.append(attr)
            elif stream.curr.type == "method":
                stream, method = Parser.parse_method(stream)
                body.append(method)
            elif stream.curr.type == "new":
                stream, constructor = Parser.parse_constructor(stream)
                body.append(constructor)
            else:
                raise stream.error(f"Class body must contain only attrs, methods, and constructors")
        stream, _ = stream.expect("}")
        return stream, Class(name, bases, body)

    @staticmethod
    @parsing_method
    def parse_attr(stream: Stream) -> (Stream, Attr):
        stream, _ = stream.expect("attr")
        stream, name_token = stream.expect("ident")
        name = name_token.text
        if stream.curr.type == ":":
            stream, _ = stream.expect(":")
            stream, type = Parser.parse_type(stream)
        else:
            type = None
        stream, _ = stream.expect(";")
        return stream, Attr(name, type)

    @staticmethod
    @parsing_method
    def parse_method(stream: Stream) -> (Stream, Method):
        stream, _ = stream.expect("method")
        stream, name = stream.expect("ident")

        def parse_parameter(s: Stream):
            s, param_name = s.expect("ident")
            s, _ = s.expect(":")
            s, typ = Parser.parse_type(s)
            return s, (param_name.text, typ)

        stream, arg_tuples = Parser.arguments("(", stream, parse_parameter, ")")
        args = dict(arg_tuples)
        if stream.curr.type == "->":
            stream, _ = stream.expect("->")
            stream, ret = Parser.parse_type(stream)
        else:
            ret = None
        body = []
        stream, _ = stream.expect("{")
        while not stream.curr.type == "}":
            stream, stmt = Parser.parse_statement(stream)
            body.append(stmt)
        stream, _ = stream.expect("}")
        return stream, Method(name.text, args=args, ret=ret, body=body)

    @staticmethod
    @parsing_method
    def parse_constructor(stream: Stream):
        stream, _ = stream.expect("new")

        def parse_parameter(s: Stream):
            s, param_name = s.expect("ident")
            s, _ = s.expect(":")
            s, typ = Parser.parse_type(s)
            return s, (param_name.text, typ)

        stream, arg_tuples = Parser.arguments("(", stream, parse_parameter, ")")
        args = dict(arg_tuples)
        body = []
        stream, _ = stream.expect("{")
        while not stream.curr.type == "}":
            stream, stmt = Parser.parse_statement(stream)
            body.append(stmt)
        stream, _ = stream.expect("}")
        return stream, Constructor(args, body)

    @staticmethod
    @parsing_method
    def parse_statement(stream: Stream) -> (Stream, Stmt):
        if stream.curr.type == "var":
            return Parser.parse_var_stmt(stream)
        elif stream.curr.type == "return":
            return Parser.parse_return_stmt(stream)
        elif stream.curr.type == "if":
            return Parser.parse_if_stmt(stream)
        elif stream.curr.type == "{":
            return Parser.parse_block(stream)
        else:
            return Parser.parse_expr_stmt(stream)

    @staticmethod
    @parsing_method
    def parse_block(stream: Stream):
        stream, _ = stream.expect("{")
        body = []
        while not stream.curr.type == "}":
            stream, stmt = Parser.parse_statement(stream)
            body.append(stmt)
        stream, _ = stream.expect("}")
        return stream, Block(body)

    @staticmethod
    @parsing_method
    def parse_if_stmt(stream: Stream):
        stream, _ = stream.expect("if")
        stream, _ = stream.expect("(")
        stream, cond = Parser.parse_expr(stream)
        stream, _ = stream.expect(")")
        stream, then_do = Parser.parse_statement(stream)
        if stream.curr.type == 'else':
            stream, _ = stream.expect("else")
            stream, else_do = Parser.parse_statement(stream)
        else:
            else_do = Block([])
        return stream, IfStmt(cond, then_do, else_do)

    @staticmethod
    @parsing_method
    def parse_var_stmt(stream: Stream):
        stream, _ = stream.expect("var")
        stream, var = stream.expect("ident")

        stream, _ = stream.expect(":")

        stream, typ = Parser.parse_type(stream)

        if stream.curr.type == "=":
            stream, _ = stream.expect("=")
            stream, val = Parser.parse_expr(stream)
        else:
            val = None
        stream, _ = stream.expect(";")
        return stream, VarStmt(var.text, typ, val)

    @staticmethod
    @parsing_method
    def parse_return_stmt(stream: Stream):
        stream, _ = stream.expect("return")
        if stream.curr.type == ";":
            stream, _ = stream.expect(";")
            # noinspection PyTypeChecker
            return stream, ReturnStmt(None)
        stream, expr = Parser.parse_expr(stream)
        stream, _ = stream.expect(";")
        return stream, ReturnStmt(expr)

    @staticmethod
    @parsing_method
    def parse_expr_stmt(stream: Stream):
        stream, expr = Parser.parse_expr(stream)
        stream, _ = stream.expect(";")
        return stream, ExprStmt(expr)

    @staticmethod
    @parsing_method
    def parse_expr(stream: Stream):
        return Parser.parse_assignment(stream)

    @staticmethod
    @parsing_method
    def parse_assignment(stream: Stream):
        stream, expr = Parser.parse_equality(stream)
        if stream.curr.type == "=":
            if isinstance(expr, GetVar):
                stream, _ = stream.expect("=")
                stream, right = Parser.parse_assignment(stream)
                expr = SetVar(expr.var, right)
            elif isinstance(expr, GetAttr):
                stream, _ = stream.expect("=")
                stream, right = Parser.parse_assignment(stream)
                expr = SetAttr(expr.obj, expr.attr, right)
            else:
                stream.error(f"Left-hand side of an assignment must be a variable")

        return stream, expr

    @staticmethod
    def parse_bin_op(stream: Stream, ops: List[str], lower) -> (Stream, Expr):
        stream, expr = lower(stream)
        while stream.curr.type in ops:
            start = stream.curr.line, stream.curr.pos
            stream, op = stream.advance()
            stream, right = lower(stream)
            expr = BinOp(left=expr, op=op.text, right=right)
            expr.place(*start)
        return stream, expr

    @staticmethod
    @parsing_method
    def parse_equality(stream: Stream) -> (Stream, BinOp):
        return Parser.parse_bin_op(stream, ["==", "!="], Parser.parse_comparison)

    @staticmethod
    @parsing_method
    def parse_comparison(stream: Stream) -> (Stream, BinOp):
        return Parser.parse_bin_op(stream, ["<", ">", "<=", ">="], Parser.parse_addition)

    @staticmethod
    @parsing_method
    def parse_addition(stream: Stream) -> (Stream, BinOp):
        return Parser.parse_bin_op(stream, ["+", "-"], Parser.parse_multiplication)

    @staticmethod
    @parsing_method
    def parse_multiplication(stream: Stream) -> (Stream, BinOp):
        return Parser.parse_bin_op(stream, ["*", "/", "//", "%"], Parser.parse_cast)

    @staticmethod
    @parsing_method
    def parse_cast(stream: Stream):
        stream, expr = Parser.parse_unary(stream)
        while stream.curr.type == "as":
            start = stream.curr.line, stream.curr.pos
            stream, _ = stream.expect("as")
            stream, typ = Parser.parse_type(stream)
            expr = Cast(expr, typ)
            expr.place(*start)
        return stream, expr

    @staticmethod
    @parsing_method
    def parse_unary(stream: Stream) -> (Stream, Unary):
        if stream.curr.type in ("!", "-"):
            stream, op = stream.advance()
            stream, right = Parser.parse_unary(stream)
            return Unary(op.text, right)
        else:
            return Parser.parse_call(stream)

    @staticmethod
    @parsing_method
    def parse_call(stream: Stream):
        stream, expr = Parser.parse_primary(stream)
        while True:
            start = stream.curr.line, stream.curr.pos
            if stream.curr.type == "(":
                stream, args = Parser.arguments("(", stream, Parser.parse_expr, ")")
                expr = Call(expr, args)
            elif stream.curr.type == ".":
                stream, _ = stream.expect(".")
                stream, attr = stream.expect("ident")
                expr = GetAttr(expr, attr.text)
            else:
                break
            expr.place(*start)
        return stream, expr

    @staticmethod
    @parsing_method
    def parse_primary(stream: Stream):
        if stream.curr.type == "ident":
            stream, var = stream.advance()
            return stream, GetVar(var.text)
        elif stream.curr.type in ("num", "hex", "str"):
            type = stream.curr.type
            stream, literal = stream.advance()
            # noinspection PyTypeChecker
            return stream, Literal(type, literal.text)
        elif stream.curr.type == "(":
            stream, _ = stream.expect("(")
            stream, expr = Parser.parse_expr(stream)
            stream, _ = stream.expect(")")
            return stream, Grouping(expr)
        elif stream.curr.type == "new":
            stream, _ = stream.expect("new")
            stream, cls = Parser.parse_type(stream)
            stream, args = Parser.arguments("(", stream, Parser.parse_expr, ")")
            return stream, New(cls, args)
        else:
            stream.error(f"Expected Expression, got {stream.curr.type}")


def parse(tokens: List[Token]):
    return Parser.parse_program(Stream(tokens))
