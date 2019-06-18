from __future__ import annotations

from typing import List, Dict

from dragon.common.dragon_ast import *

from dragon.common import Token, DragonError

ORDER = "AFTER scanner"


class ParseError(DragonError):
    pass


class Stream:
    def __init__(self, tokens: List[Token], macro_symbols: Dict[str, Dict[str, Node]] = None):
        if macro_symbols is None:
            macro_symbols = {"stmt": {}, "expr": {}}
        else:
            assert "stmt" in macro_symbols and "expr" in macro_symbols
        self.tokens = tokens
        self.macro_symbols = macro_symbols

    @property
    def curr(self) -> Token:
        try:
            return self.tokens[0]
        except IndexError:
            return Token("\0", "\0", 0, (0, 0))

    def advance(self):
        return Stream(self.tokens[1:], self.macro_symbols), self.tokens[0]

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
    def _wrapper(self, stream: Stream):
        new_stream, node = func(self, stream)
        if node is not None:
            node.place(stream.curr.line, stream.curr.pos)
        return new_stream, node
    return _wrapper


class Macro:
    def __init__(self, start: str, call: List[Token], replace: List[Token]):
        self.start = start
        self.call = call
        self.replace = replace

    def apply(self, parser: Parser, stream: Stream):
        # stream, start = stream.expect("ident")
        # assert start.text == self.start

        def get_else(li, ind, default=None):
            try:
                return li[ind]
            except IndexError:
                return default

        symbols = {"stmt": {}, "expr": {}}

        call_iter = enumerate(iter(self.call))
        for n, call_token in call_iter:
            if not call_token.type.startswith("$"):
                after_stream, token = stream.advance()
                if not token == call_token:
                    raise stream.error(f"Macro expected {call_token}, got {token}")
                stream = after_stream
            else:
                type = call_token.type[1:]
                if type == "ident":
                    if (get_else(self.call, n + 1) and get_else(self.call, n + 2)
                            and self.call[n + 1].type == ":" and self.call[n + 2].type == "ident"):
                        rule = self.call[n + 2].text
                        ident = call_token.text
                        # ident, rule = call_token.text.split(" ")
                        stream, node = getattr(parser, "parse_" + rule)(stream)
                        symbols[rule][ident] = node
                        next(call_iter)
                        next(call_iter)
                    else:
                        raise ParseError(f"Macro argument must be of form $identifier:type, not {call_token.text!r}",
                                         call_token.line, call_token.pos)
                else:
                    raise Exception()

        macro_tokens = self.replace
        macro_stream = Stream(macro_tokens, symbols)
        return stream, macro_stream


class Parser:
    def __init__(self):
        self.macros: Dict[str, Dict[str, Macro]] = {
            "stmt": {},
            "expr": {}
        }

    def parse_program(self, stream: Stream) -> Program:
        top_levels = []
        while not stream.is_empty():
            stream, top_level = self.parse_top_level(stream)
            if top_level is not None:
                top_levels.append(top_level)
        program = Program(top_levels)
        program.place(0, (0, 0))
        return program

    @parsing_method
    def parse_top_level(self, stream: Stream) -> (Stream, TopLevel):
        if stream.curr.type == 'class':
            return self.parse_class(stream)
        elif stream.curr.type == 'def':
            return self.parse_function(stream)
        elif stream.curr.type == 'macro':
            stream = self.parse_macro(stream)
            return stream, None
        elif stream.curr.type == "import":
            return self.parse_import(stream)
        else:
            raise stream.error(f"Cannot parse a top level statement from a '{stream.curr.type}' token")

    @parsing_method
    def parse_import(self, stream: Stream):
        stream, _ = stream.expect("import")
        stream, file = stream.expect("str")
        return stream, Import(file.text[1:-1])

    def parse_macro(self, stream: Stream) -> Stream:
        stream, _ = stream.expect("macro")

        macro_call = []

        stream, _ = stream.expect("$(")
        stream, start = stream.expect("ident")
        macro_call.append(start)
        while stream.curr.type != ")$":
            stream, token = stream.advance()
            macro_call.append(token)
        stream, _ = stream.expect(")$")

        stream, _ = stream.expect("=>")
        stream, ret_token = stream.expect("ident")
        place = ret_token.text
        stream, _ = stream.expect(":")

        macro_replace = []

        stream, _ = stream.expect("$(")
        while stream.curr.type != ")$":
            stream, token = stream.advance()
            macro_replace.append(token)
        stream, _ = stream.expect(")$")

        macro = Macro(start.text, macro_call, macro_replace)

        self.macros[place][macro.start] = macro

        stream, _ = stream.expect("endmacro")

        return stream

    def arguments(self, start: str, stream: Stream, each, end: str) -> (Stream, List):
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

    @parsing_method
    def parse_type(self, stream: Stream):
        return self.parse_generic(stream)

    @parsing_method
    def parse_generic(self, stream: Stream):
        stream, type = self.parse_dotted_name(stream)
        while stream.curr.type == "<":
            stream, args = self.arguments("<", stream, self.parse_type, ">")
            type = Generic(type, args)
        return stream, type

    @parsing_method
    def parse_dotted_name(self, stream: Stream):
        stream, type = self.parse_name(stream)
        while stream.curr.type == ".":
            stream, _ = stream.expect(".")
            stream, attr = stream.expect("ident")
            type = GetName(type, attr.text)
        return stream, type

    @parsing_method
    def parse_name(self, stream: Stream):
        stream, name = stream.expect("ident")
        type = Name(name.text)
        return stream, type

    @parsing_method
    def parse_function(self, stream: Stream):
        stream, _ = stream.expect("def")
        stream, name = stream.expect("ident")

        def parse_parameter(s: Stream):
            s, param_name = s.expect("ident")
            s, _ = s.expect(":")
            s, typ = self.parse_type(s)
            return s, (param_name.text, typ)

        stream, arg_tuples = self.arguments("(", stream, parse_parameter, ")")
        args = dict(arg_tuples)
        if stream.curr.type == "->":
            stream, _ = stream.expect("->")
            stream, ret = self.parse_type(stream)
        else:
            ret = None
        body = []
        stream, _ = stream.expect("{")
        while not stream.curr.type == "}":
            stream, stmt = self.parse_stmt(stream)
            body.append(stmt)
        stream, _ = stream.expect("}")
        return stream, Function(name.text, args=args, ret=ret, body=body)

    @parsing_method
    def parse_class(self, stream: Stream) -> (Stream, Class):
        stream, _ = stream.expect("class")
        stream, name_token = stream.expect("ident")
        name = name_token.text

        if stream.curr.type == "<":
            stream, type_vars = self.arguments("<", stream, self.parse_name, ">")
            type_vars = [type_var.name for type_var in type_vars]
        else:
            type_vars = []

        if stream.curr.type == "(":
            stream, bases = self.arguments("(", stream, self.parse_type, ")")
        else:
            bases = []

        body = []
        stream, _ = stream.expect("{")
        while not stream.curr.type == "}":
            if stream.curr.type == "attr":
                stream, attr = self.parse_attr(stream)
                body.append(attr)
            elif stream.curr.type == "method":
                stream, method = self.parse_method(stream)
                body.append(method)
            elif stream.curr.type == "new":
                stream, constructor = self.parse_constructor(stream)
                body.append(constructor)
            else:
                raise stream.error(f"Class body must contain only attrs, methods, and constructors")
        stream, _ = stream.expect("}")
        if type_vars:
            # noinspection PyArgumentList
            return stream, GenericClass(name, bases, body, type_vars)
        else:
            return stream, Class(name, bases, body)

    @parsing_method
    def parse_attr(self, stream: Stream) -> (Stream, Attr):
        stream, _ = stream.expect("attr")
        stream, name_token = stream.expect("ident")
        name = name_token.text
        if stream.curr.type == ":":
            stream, _ = stream.expect(":")
            stream, type = self.parse_type(stream)
        else:
            type = None
        stream, _ = stream.expect(";")
        return stream, Attr(name, type)

    @parsing_method
    def parse_method(self, stream: Stream) -> (Stream, Method):
        stream, _ = stream.expect("method")
        stream, name = stream.expect("ident")

        def parse_parameter(s: Stream):
            s, param_name = s.expect("ident")
            s, _ = s.expect(":")
            s, typ = self.parse_type(s)
            return s, (param_name.text, typ)

        stream, arg_tuples = self.arguments("(", stream, parse_parameter, ")")
        args = dict(arg_tuples)
        if stream.curr.type == "->":
            stream, _ = stream.expect("->")
            stream, ret = self.parse_type(stream)
        else:
            ret = None
        body = []
        stream, _ = stream.expect("{")
        while not stream.curr.type == "}":
            stream, stmt = self.parse_stmt(stream)
            body.append(stmt)
        stream, _ = stream.expect("}")
        return stream, Method(name.text, args=args, ret=ret, body=body)

    @parsing_method
    def parse_constructor(self, stream: Stream):
        stream, _ = stream.expect("new")

        def parse_parameter(s: Stream):
            s, param_name = s.expect("ident")
            s, _ = s.expect(":")
            s, typ = self.parse_type(s)
            return s, (param_name.text, typ)

        stream, arg_tuples = self.arguments("(", stream, parse_parameter, ")")
        args = dict(arg_tuples)
        body = []
        stream, _ = stream.expect("{")
        while not stream.curr.type == "}":
            stream, stmt = self.parse_stmt(stream)
            body.append(stmt)
        stream, _ = stream.expect("}")
        return stream, Constructor(args, body)

    @parsing_method
    def parse_stmt(self, stream: Stream) -> (Stream, Stmt):
        if stream.curr.type == "var":
            return self.parse_var_stmt(stream)
        elif stream.curr.type == "return":
            return self.parse_return_stmt(stream)
        elif stream.curr.type == "if":
            return self.parse_if_stmt(stream)
        elif stream.curr.type == "while":
            return self.parse_while_stmt(stream)
        elif stream.curr.type == "{":
            return self.parse_block(stream)
        elif stream.curr.type == "ident" and stream.curr.text in self.macros["stmt"]:
            macro = self.macros["stmt"][stream.curr.text]
            stream, macro_stream = macro.apply(self, stream)
            return stream, self.parse_stmt(macro_stream)[1]
        elif stream.curr.type == "$ident" and stream.curr.text in stream.macro_symbols["stmt"]:
            # if stream.curr.text in stream.macro_symbols["stmt"]:
            stream, ident = stream.advance()
            return stream, stream.macro_symbols["stmt"][ident.text]
        elif stream.curr.type == "del":
            return self.parse_delete(stream)
        # else:
        #     raise stream.error(f"Statement meta-identifier {stream.curr.text} is not defined")
        else:
            return self.parse_expr_stmt(stream)

    @parsing_method
    def parse_delete(self, stream: Stream):
        stream, _ = stream.expect("del")
        stream, obj = self.parse_expr(stream)
        stream, _ = stream.expect(";")
        return stream, DeleteStmt(obj)

    @parsing_method
    def parse_block(self, stream: Stream):
        stream, _ = stream.expect("{")
        body = []
        while not stream.curr.type == "}":
            stream, stmt = self.parse_stmt(stream)
            body.append(stmt)
        stream, _ = stream.expect("}")
        return stream, Block(body)

    @parsing_method
    def parse_if_stmt(self, stream: Stream):
        stream, _ = stream.expect("if")
        stream, _ = stream.expect("(")
        stream, cond = self.parse_expr(stream)
        stream, _ = stream.expect(")")
        stream, then_do = self.parse_stmt(stream)
        if stream.curr.type == 'else':
            stream, _ = stream.expect("else")
            stream, else_do = self.parse_stmt(stream)
        else:
            else_do = Block([])
        return stream, IfStmt(cond, then_do, else_do)

    @parsing_method
    def parse_while_stmt(self, stream: Stream):
        stream, _ = stream.expect("while")
        stream, _ = stream.expect("(")
        stream, cond = self.parse_expr(stream)
        stream, _ = stream.expect(")")
        stream, body = self.parse_stmt(stream)
        return stream, WhileStmt(cond, body)

    @parsing_method
    def parse_var_stmt(self, stream: Stream):
        stream, _ = stream.expect("var")
        stream, var = stream.expect("ident")

        stream, _ = stream.expect(":")

        stream, typ = self.parse_type(stream)

        if stream.curr.type == "=":
            stream, _ = stream.expect("=")
            stream, val = self.parse_expr(stream)
        else:
            val = None
        stream, _ = stream.expect(";")
        return stream, VarStmt(var.text, typ, val)

    @parsing_method
    def parse_return_stmt(self, stream: Stream):
        stream, _ = stream.expect("return")
        if stream.curr.type == ";":
            stream, _ = stream.expect(";")
            # noinspection PyTypeChecker
            return stream, ReturnStmt(None)
        stream, expr = self.parse_expr(stream)
        stream, _ = stream.expect(";")
        return stream, ReturnStmt(expr)

    @parsing_method
    def parse_expr_stmt(self, stream: Stream):
        stream, expr = self.parse_expr(stream)
        stream, _ = stream.expect(";")
        return stream, ExprStmt(expr)

    @parsing_method
    def parse_expr(self, stream: Stream):
        # if stream.curr.type == "ident":
        #     var = stream.curr.text
        #     if var in self.macros["expr"]:
        #         macro = self.macros["expr"][var]
        #         stream, macro_stream = macro.apply(self, stream)
        #         return stream, self.parse_expr(macro_stream)[1]

        return self.parse_assignment(stream)

    @parsing_method
    def parse_assignment(self, stream: Stream):
        stream, expr = self.parse_equality(stream)
        if stream.curr.type == "=":
            if isinstance(expr, GetVar):
                stream, _ = stream.expect("=")
                stream, right = self.parse_assignment(stream)
                expr = SetVar(expr.var, right)
            elif isinstance(expr, GetAttr):
                stream, _ = stream.expect("=")
                stream, right = self.parse_assignment(stream)
                expr = SetAttr(expr.obj, expr.attr, right)
            else:
                stream.error(f"Left-hand side of an assignment must be a variable or attribute")

        return stream, expr

    def parse_bin_op(self, stream: Stream, ops: List[str], lower) -> (Stream, Expr):
        stream, expr = lower(stream)
        while stream.curr.type in ops:
            start = stream.curr.line, stream.curr.pos
            stream, op = stream.advance()
            stream, right = lower(stream)
            expr = BinOp(left=expr, op=op.text, right=right)
            expr.place(*start)
        return stream, expr

    @parsing_method
    def parse_equality(self, stream: Stream) -> (Stream, BinOp):
        return self.parse_bin_op(stream, ["==", "!="], self.parse_comparison)

    @parsing_method
    def parse_comparison(self, stream: Stream) -> (Stream, BinOp):
        return self.parse_bin_op(stream, ["<", ">", "<=", ">="], self.parse_addition)

    @parsing_method
    def parse_addition(self, stream: Stream) -> (Stream, BinOp):
        return self.parse_bin_op(stream, ["+", "-"], self.parse_multiplication)

    @parsing_method
    def parse_multiplication(self, stream: Stream) -> (Stream, BinOp):
        return self.parse_bin_op(stream, ["*", "/", "//", "%"], self.parse_cast)

    @parsing_method
    def parse_cast(self, stream: Stream):
        stream, expr = self.parse_unary(stream)
        while stream.curr.type == "as":
            start = stream.curr.line, stream.curr.pos
            stream, _ = stream.expect("as")
            stream, typ = self.parse_type(stream)
            expr = Cast(expr, typ)
            expr.place(*start)
        return stream, expr

    @parsing_method
    def parse_unary(self, stream: Stream) -> (Stream, Unary):
        if stream.curr.type in ("!", "-"):
            stream, op = stream.advance()
            stream, right = self.parse_unary(stream)
            return Unary(op.text, right)
        else:
            return self.parse_call(stream)

    @parsing_method
    def parse_call(self, stream: Stream):
        stream, expr = self.parse_primary(stream)
        while not stream.is_empty():
            start = stream.curr.line, stream.curr.pos
            if stream.curr.type == "(":
                stream, args = self.arguments("(", stream, self.parse_expr, ")")
                expr = Call(expr, args)
            elif stream.curr.type == ".":
                stream, _ = stream.expect(".")
                stream, attr = stream.expect("ident")
                expr = GetAttr(expr, attr.text)
            else:
                break
            expr.place(*start)
        return stream, expr

    @parsing_method
    def parse_primary(self, stream: Stream):
        if stream.curr.type == "ident":
            if stream.curr.text in self.macros["expr"]:
                macro = self.macros["expr"][stream.curr.text]
                stream, macro_stream = macro.apply(self, stream)
                return stream, self.parse_expr(macro_stream)[1]
            stream, var = stream.advance()
            return stream, GetVar(var.text)
        elif stream.curr.type == "$ident":
            if stream.curr.text in stream.macro_symbols["expr"]:
                stream, ident = stream.advance()
                return stream, stream.macro_symbols["expr"][ident.text]
            else:
                raise stream.error(f"Expression meta-identifier {stream.curr.text} is not defined")
        elif stream.curr.type in ("num", "hex", "str"):
            type = stream.curr.type
            stream, literal = stream.advance()
            # noinspection PyTypeChecker
            return stream, Literal(type, literal.text)
        elif stream.curr.type == "(":
            stream, _ = stream.expect("(")
            stream, expr = self.parse_expr(stream)
            stream, _ = stream.expect(")")
            return stream, Grouping(expr)
        elif stream.curr.type == "new":
            stream, _ = stream.expect("new")
            stream, cls = self.parse_type(stream)
            stream, args = self.arguments("(", stream, self.parse_expr, ")")
            return stream, New(cls, args)
        else:
            stream.error(f"Expected Expression, got {stream.curr.type}")


def parse(tokens: List[Token]):
    parser = Parser()
    return parser.parse_program(Stream(tokens))
