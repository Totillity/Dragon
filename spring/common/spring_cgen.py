from typing import Tuple
from .mutable_dict import MutableDict

from ._cgen import *


class ClassType(DataType):
    def __init__(self, name: str, bases: List['ClassType']):
        """
        Parameters:
             name (str): The C NAME of this class
        """
        self.typ = "struct " + name + "*"

        self.name = name
        """The C NAME of this class"""

        self.bases = bases
        """A list of ClassTypes which are the bases to this class"""

        self.attrs: Dict[str, Type] = {}
        self.methods: Dict[str, PointerType] = {}

        self.other: Dict[str, Type] = {}
        """The type of new, del and other special attributes"""

        self.func_names: Dict[str, str] = {}
        """A dict mapping the spring name of a method or other to the c function name where it's implemented"""

        self.struct = StructType(name)

    @property
    def names(self):
        return tuple(self.attrs.keys()) + tuple(self.methods.keys()) + tuple(self.other.keys())

    def add_name(self, name: str, ):
        pass

    def has_name(self, name: str):
        if name in self.names:
            return True
        else:
            for base in self.bases:
                if base.has_name(name):
                    return True
            else:
                return False

    def get_name(self, name: str) -> Type:
        """
        Returns:
             Type: the type of the attribute `name` of this class (or its bases)
        Raises:
            KeyError: If `name` is not an attribute of this class or any of its bases
        """
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

    def get_func_name(self, name: str) -> str:
        """
        Args:
            name (str): The name of the method or other to query
        Returns:
            str: The c name of the function which implements the method or other name
        Raises:
            KeyError: If `name` is not an attribute of this class or any of its bases
        """
        if name in self.func_names:
            return self.func_names[name]
        else:
            for base in self.bases:
                try:
                    return base.get_func_name(name)
                except KeyError:
                    pass
            raise KeyError(name)

    def get_name_expr(self, obj: Expression, name: str) -> Expression:
        """
        Args:
            obj (Expression): The cgen node which represents an object of type `self`
            name (str): The name of the attribute to get
        Returns:
            Expression: A cgen Expression which gets the attribute `name`
        Raises:
            KeyError: If `name` is not an attribute of this class or any of its bases
        """
        if name in self.methods or name in self.attrs:
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
        """
        Args:
            obj (Expression): The cgen node which represents an object of type `self`
            name (str): The name of the attribute to set
            val (Expression): What to set `obj`.`name` to
        Returns:
            Expression: A cgen Expression which sets the attribute `name` to `val`
        Raises:
            KeyError: If `name` is not an attribute of this class or any of its bases
        """
        if name in self.methods or name in self.attrs:
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
        if name in self.func_names:
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


class CustomType(DataType):
    def __init__(self, typ):
        self.typ = typ


class FuncType(Type, ABC):
    @abstractmethod
    def ret_for(self, args: List[Type]) -> Type:
        pass

    @abstractmethod
    def type_for(self, args: List[Type]) -> 'SingleFuncType':
        pass

    @abstractmethod
    def c_name_for(self, args: List[Type]) -> str:
        pass


class SingleFuncType(FuncType, FunctionType):
    def __init__(self, args: List[Type], ret: Type, c_name: str):
        super().__init__(args, ret)
        self.c_name = c_name

    def ret_for(self, args: List[Type]):
        # TODO argument validation
        return self.ret

    def type_for(self, args: List[Type]):
        return self

    def as_type(self, ptrs=0):
        return super().as_type(ptrs + 1)

    def c_name_for(self, args: List[Type]):
        return self.c_name

    def with_name(self, name: str, ptrs=0):
        return super().with_name(name, ptrs + 1)

    def as_func_ret(self, name: str, ptrs=0):
        return super().as_func_ret(name, ptrs + 1)

    def as_func_ret_def(self, name: str, func_args: Dict[str, Type], ptrs=0):
        return super().as_func_ret_def(name, func_args, ptrs + 1)


class OverloadedFuncType(FuncType):
    def __init__(self, overloads: MutableDict[Tuple[Dict[str, Type], Type], str]):
        self.overloads = overloads

    def ret_for(self, args: List[Type]):
        for overload_args, ret in self.overloads.keys():
            if [typ for _, typ in overload_args.items()] == args:
                return ret
        raise KeyError()

    def type_for(self, args: List[Type]):
        for (overload_args, ret), c_name in self.overloads.items():
            if [typ for _, typ in overload_args.items()] == args:
                return SingleFuncType(args, ret, c_name)
        raise KeyError()

    def c_name_for(self, args: List[Type]):
        for (overload_args, ret), c_name in self.overloads.items():
            if [typ for _, typ in overload_args.items()] == args:
                return c_name
        raise KeyError()

    def as_type(self, ptrs=0):
        raise NotImplementedError()

    def as_func_ret(self, name: str, ptrs=0):
        raise NotImplementedError()

    def as_func_ret_def(self, name: str, func_args: Dict[str, Type], ptrs=0):
        raise NotImplementedError()

    def with_name(self, name: str, ptrs=0) -> str:
        raise NotImplementedError()


def is_int(typ):
    return typ is Int


def is_cls(typ):
    return isinstance(typ, ClassType)


def is_func_ptr(typ):
    return isinstance(typ, FuncType)


def is_void(typ):
    return typ is Void


def inc_ref(node: Expression) -> Expression:
    return Call(GetVar("drgn_inc_ref"), [node])


def dec_refs(nodes: Iterable[Expression]) -> Statement:
    return UnscopedBlock([ExprStmt(Call(GetVar("DRGN_DECREF"), [node])) for node in nodes])


CInt = IntType()

Void = VoidType()
VoidPtr = PointerType(Void)
Int = CustomType("int32_t")
Bool = BoolType()


BaseObject = StructType("BaseObject")


Object = ClassType("Object", [])

Integer = ClassType("Integer", [Object])
String = ClassType("String", [Object])
C_Array = ClassType("_Array", [Object])

Object.methods = {"to_string": SingleFuncType([Object], String, "Object_to_string")}
Object.func_names = {"to_string": "Object_to_string"}

String.methods = {"get_item": SingleFuncType([String, Int], String, "String_get_item")}
String.func_names = {"get_item": "String_get_item"}

C_Array.methods = {"get_item": SingleFuncType([C_Array, Int], Object, "_Array_get_item"),
                   "set_item": SingleFuncType([C_Array, Int, Object], Void, "_Array_set_item")}
C_Array.other = {"new": SingleFuncType([Int], C_Array, "new")}
C_Array.func_names = {"get_item": "_Array_get_item",
                      "set_item": "_Array_set_item",
                      "new": "new__Array"}
