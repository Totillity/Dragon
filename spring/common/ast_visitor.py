from .spring_ast import Node


class Visitor:
    def visit(self, obj: Node, *args, **kwargs):
        try:
            method = getattr(self, "visit_" + obj.__class__.__name__)
        except AttributeError:
            method = self.default

        return method(obj, *args, **kwargs)

    def default(self, obj, *args, **kwargs):
        raise AttributeError("No visitor for " + repr(obj))
