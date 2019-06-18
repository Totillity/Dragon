from typing import Tuple

from ._cgen import *


class VoidPointerType(DataType):
    typ = 'void*'


class StringType(DataType):
    typ = 'char*'


class ClassType(DataType):
    def __init__(self, name: str, bases: List['ClassType']):
        self.typ = "struct " + name + "*"
        self.name = name
        self.bases = bases
        self.attrs: Dict[str, Type] = {}
        self.methods: Dict[str, PointerType] = {}
        self.other: Dict[str, Type] = {}

        self.c_names: Dict[str, str] = {}

        self.struct = StructType(name)

    def has_name(self, name: str):
        if name in self.c_names:
            return True
        else:
            for base in self.bases:
                if base.has_name(name):
                    return True
            else:
                return False

    def get_name(self, name: str) -> Type:
        if name in self.attrs:
            return self.attrs[name]
        elif name in self.methods:
            return self.methods[name]
        else:
            for base in self.bases:
                try:
                    return base.get_name(name)
                except KeyError:
                    pass
            else:
                raise KeyError(name)

    def get_c_name(self, name: str) -> str:
        if name in self.c_names:
            return self.c_names[name]
        else:
            for base in self.bases:
                try:
                    return base.get_c_name(name)
                except KeyError:
                    pass
            raise KeyError(name)

    def get_name_expr(self, obj: Expression, name: str):
        if name in self.c_names or name in self.attrs:
            return GetAttr(obj, name)
        else:
            for base in self.bases:
                try:
                    return base.get_name_expr(GetAttr(obj, 'parent_' + base.name), name)
                except KeyError:
                    pass
            else:
                raise KeyError(name)

    def set_name_expr(self, obj: Expression, name: str, val: Expression):
        if name in self.c_names or name in self.attrs:
            return SetAttr(obj, name, val)
        else:
            for base in self.bases:
                try:
                    return base.set_name_expr(GetAttr(obj, 'parent_'+base.name), name, val)
                except KeyError:
                    pass
            raise KeyError(name)

    def path_to_parent(self, typ: 'ClassType'):
        if typ is self:
            return [self]
        else:
            for base in self.bases:
                try:
                    return base.path_to_parent(typ) + [self]
                except KeyError:
                    pass
            raise KeyError(typ)

    def cast_expr(self, obj: Expression, typ: 'ClassType'):
        if typ is self:
            return obj
        else:
            for base in self.bases:
                try:
                    return base.cast_expr(GetAttr(obj, 'parent_'+base.name), typ)
                except KeyError:
                    pass
            raise KeyError(typ)

    def cast_for_name_expr(self, obj: Expression, name: str):
        if name in self.c_names:
            return obj
        else:
            for base in self.bases:
                try:
                    return base.cast_for_name_expr(GetAttr(obj, 'parent_'+base.name), name)
                except KeyError:
                    pass
            raise KeyError(name)

    def all_attrs(self):
        yield from self.attrs.items()

        for base in self.bases:
            yield from base.all_attrs()

    def all_methods(self):
        yield from self.methods.keys()

        for base in self.bases:
            yield from base.all_methods()

    def __repr__(self):
        return f"ClassType({self.name})"

    @property
    def fields(self):
        fields = {}
        fields.update({'parent_'+base.name: base.struct for base in self.bases})
        fields.update(self.attrs)
        fields.update(self.methods)
        fields.update(self.other)
        return fields


class GenericClassType(DataType):
    def __init__(self, name: str, type_vars: List[str], node, scope):
        self.name = name
        self.type_vars = type_vars
        self.node = node
        self.scope = scope

        self.generics: Dict[Tuple[str, ...], ClassType] = {}


class NullType(DataType):
    typ = "int"


def dragon_function(args: List[Type], ret: Type):
    return PointerType(FunctionType(args, ret))


BaseObject = StructType("BaseObject")


Object = ClassType("Object", [])

Integer = ClassType("Integer", [Object])
String = ClassType("String", [Object])
C_Array = ClassType("_Array", [Object])


Object.methods = {"to_string": PointerType(FunctionType([Object], String))}
Object.c_names = {"to_string": "Object_to_string"}

C_Array.methods = {"get_item": PointerType(FunctionType([C_Array, IntType()], Object)),
                   "set_item": PointerType(FunctionType([C_Array, IntType(), Object], VoidType()))}
C_Array.other = {"new": PointerType(FunctionType([IntType()], C_Array))}
C_Array.c_names = {"get_item": "_Array_get_item",
                   "set_item": "_Array_set_item",
                   "new": "new__Array"}
