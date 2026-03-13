"""Node visitor for expr nodes."""

import ast

from rubberize._exceptions import RubberizeNotImplementedError
from rubberize.config import config
from rubberize.latexer import helpers, formatters, ranks, rules
from rubberize.latexer.calls import convert_call
from rubberize.latexer.expr_latex import ExprLatex
from rubberize.latexer.objects import convert_object


# pylint: disable=invalid-name,too-many-public-methods
class ExprVisitor(ast.NodeVisitor):
    """Node visitor for ast.expr nodes.

    Each visitor method returns an ExprLatex for the node.
    """

    def __init__(
        self, ns: dict[str, object] | None = None, *, is_subst: bool = False
    ) -> None:
        super().__init__()

        self.ns = ns
        self.is_subst = is_subst

    # pylint: disable-next=useless-parent-delegation
    def visit(self, node: ast.AST) -> ExprLatex:
        return super().visit(node)

    def generic_visit(self, node: ast.AST) -> ExprLatex:
        """Called if no visitor method is defined for a node."""

        raise RubberizeNotImplementedError(
            f"Unsupported ast.expr node: {type(node).__name__!r}"
        )

    def visit_BoolOp(self, node: ast.BoolOp) -> ExprLatex:
        """Visit a boolean operation.

        Note that `not` is considered a unary operator so it is handled
        by visit_UnaryOp.
        """

        rank = ranks.get_rank(node)

        op = rules.BOOL_OPS[type(node.op)]
        values = [self.visit_operand(o, rank).latex for o in node.values]

        if len(values) > config.max_inline_elts:
            prefix, sep, suffix = rules.MULTI_BOOL_OP_SYNTAX
            latex = formatters.format_delims(
                prefix, sep(op).join(values), suffix
            )
        else:
            latex = op.join(values)

        return ExprLatex(latex, rank)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> ExprLatex:
        """Visit a named expression."""

        rank = ranks.get_rank(node)

        target = formatters.format_name(node.target.id)
        op = rules.NAMED_EXPR_OP
        value = self.visit_operand(node.value, rank).latex

        latex = f"{target}{op}{value}"

        return ExprLatex(latex, rank)

    def visit_BinOp(self, node: ast.BinOp) -> ExprLatex:
        """Visit a binary operation."""

        rank = ranks.get_rank(node)
        op = rules.BIN_OPS[type(node.op)]

        left = self.visit_binop_operand(node.left, rank, op.left)
        right = self.visit_binop_operand(node.right, rank, op.right)

        if helpers.is_unit_assignment(node, self.ns):
            return self.visit_unit_assignment(node, left, right)

        if (
            isinstance(node.op, ast.Pow)
            and isinstance(node.left, ast.Name)
            and ("^" in left.latex or "_{" in left.latex)
        ):
            left.latex = "{" + left.latex + "}"

        if config.use_contextual_mult and isinstance(node.op, ast.Mult):
            infix = helpers.get_mult_infix(node, left.latex, right.latex)
        else:
            infix = op.infix

        latex = op.prefix + left.latex + infix + right.latex + op.suffix

        return ExprLatex(latex, rank)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ExprLatex:
        """Visit a unary operation."""

        rank = ranks.get_rank(node)

        op = rules.UNARY_OPS[type(node.op)]
        operand = self.visit_operand(node.operand, rank, non_assoc=True).latex

        latex = f"{op}{operand}"

        return ExprLatex(latex, rank)

    def visit_Lambda(self, node: ast.Lambda) -> ExprLatex:
        """Visit an lambda expression."""

        ns = self.ns.copy() if self.ns else {}

        # shadow lambda args
        for name in helpers.get_store_ids(node.args):
            ns.pop(name, None)

        visitor = ExprVisitor(ns)

        rank = ranks.get_rank(node)

        args_sep = rules.LAMBDA_ARGS_SEP
        args = [formatters.format_name(a.arg) for a in node.args.args]
        op = rules.LAMBDA_OP
        body = visitor.visit_operand(node.body, rank).latex

        latex = f"{args_sep.join(args)}{op}{body}"

        return ExprLatex(latex, rank)

    def visit_IfExp(self, node: ast.IfExp) -> ExprLatex:
        """Visit an if expression."""

        cur_node: ast.expr = node

        if self.ns and self.is_subst:
            while isinstance(cur_node, ast.IfExp):
                if helpers.get_object(cur_node.test, self.ns):
                    return self.visit(cur_node.body)
                cur_node = cur_node.orelse
            return self.visit(cur_node)

        prefix, if_syntax, sep, else_syntax, suffix = rules.PIECEWISE_SYNTAX

        cur_latex: list[str] = []

        while isinstance(cur_node, ast.IfExp):
            body = self.visit(cur_node.body).latex
            test = self.visit(cur_node.test).latex
            cur_latex.append(if_syntax(body, test))
            cur_node = cur_node.orelse
        orelse = self.visit(cur_node).latex
        cur_latex.append(else_syntax(orelse))

        latex = formatters.format_delims(prefix, sep.join(cur_latex), suffix)
        rank = ranks.get_rank(node)

        return ExprLatex(latex, rank)

    def visit_Dict(self, node: ast.Dict) -> ExprLatex:
        """Visit a dict."""

        unpack: list[str] = []
        elts_dict: dict[str, str] = {}

        for k, v in zip(node.keys, node.values):
            if k is None:
                unpack.append(self.visit(v).latex)
            else:
                elts_dict[self.visit(k).latex] = self.visit(v).latex

        if len(elts_dict) > config.max_inline_elts:
            prefix, sep, suffix = rules.DICT_COL_SYNTAX
            kv_sep = rules.DICT_COL_KV_SYNTAX
        else:
            prefix, sep, suffix = rules.DICT_ROW_SYNTAX
            kv_sep = rules.DICT_ROW_KV_SYNTAX

        elts = [rf"{k}{kv_sep}{v}" for k, v in elts_dict.items()]
        latex = formatters.format_delims(prefix, sep.join(elts), suffix)

        latex = rules.UNPACKING_UNION.join([latex] + unpack)
        rank = ranks.get_rank(node)

        return ExprLatex(latex, rank)

    def visit_Set(self, node: ast.Set) -> ExprLatex:
        """Visit a set."""

        unpack: list[str] = []
        elts: list[str] = []

        for e in node.elts:
            if isinstance(e, ast.Starred):
                unpack.append(self.visit(e.value).latex)
            else:
                elts.append(self.visit(e).latex)

        if len(elts) > config.max_inline_elts:
            prefix, sep, suffix = rules.SET_COL_SYNTAX
        else:
            prefix, sep, suffix = rules.SET_ROW_SYNTAX

        latex = formatters.format_delims(prefix, sep.join(sorted(elts)), suffix)

        latex = rules.UNPACKING_UNION.join([latex] + sorted(unpack))
        rank = ranks.get_rank(node)

        return ExprLatex(latex, rank)

    def visit_ListComp(self, node: ast.ListComp) -> ExprLatex:
        """Visit a list comprehension."""

        ns = self.ns.copy() if self.ns else {}

        # shadow generator target args
        for gen in node.generators:
            for name in helpers.get_store_ids(gen.target):
                ns.pop(name, None)

        visitor = ExprVisitor(ns)

        elt = visitor.visit(node.elt).latex
        comps = r",\, ".join(visitor.visit(c).latex for c in node.generators)

        such_that = rules.COMP_SUCH_THAT
        prefix, _, suffix = rules.LIST_ROW_SYNTAX

        latex = formatters.format_delims(
            rf"{prefix}\,", f"{elt}{such_that}{comps}", rf"\,{suffix}"
        )
        rank = ranks.get_rank(node)

        return ExprLatex(latex, rank)

    def visit_SetComp(self, node: ast.SetComp) -> ExprLatex:
        """Visit a set comprehension."""

        ns = self.ns.copy() if self.ns else {}

        # shadow generator target args
        for gen in node.generators:
            for name in helpers.get_store_ids(gen.target):
                ns.pop(name, None)

        visitor = ExprVisitor(ns)

        elt = visitor.visit(node.elt).latex
        comps = r",\, ".join(visitor.visit(c).latex for c in node.generators)

        such_that = rules.COMP_SUCH_THAT
        prefix, _, suffix = rules.SET_ROW_SYNTAX

        latex = formatters.format_delims(
            rf"{prefix}\,", f"{elt}{such_that}{comps}", rf"\,{suffix}"
        )
        rank = ranks.get_rank(node)

        return ExprLatex(latex, rank)

    def visit_DictComp(self, node: ast.DictComp) -> ExprLatex:
        """Visit a dict comprehension."""

        ns = self.ns.copy() if self.ns else {}

        # shadow generator target args
        for gen in node.generators:
            for name in helpers.get_store_ids(gen.target):
                ns.pop(name, None)

        visitor = ExprVisitor(ns)

        key = visitor.visit(node.key).latex
        value = visitor.visit(node.value).latex

        elt = f"{key}{rules.DICT_ROW_KV_SYNTAX}{value}"
        comps = r",\, ".join(visitor.visit(c).latex for c in node.generators)

        such_that = rules.COMP_SUCH_THAT
        prefix, _, suffix = rules.DICT_ROW_SYNTAX

        latex = formatters.format_delims(
            rf"{prefix}\,", f"{elt}{such_that}{comps}", rf"\,{suffix}"
        )
        rank = ranks.get_rank(node)

        return ExprLatex(latex, rank)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> ExprLatex:
        """Visit a generator expression."""

        ns = self.ns.copy() if self.ns else {}

        # shadow generator target args
        for gen in node.generators:
            for name in helpers.get_store_ids(gen.target):
                ns.pop(name, None)

        visitor = ExprVisitor(ns)

        elt = visitor.visit(node.elt).latex
        comps = r",\, ".join(visitor.visit(c).latex for c in node.generators)

        latex = f"{elt}{rules.COMP_SUCH_THAT}{comps}"
        rank = ranks.get_rank(node)

        return ExprLatex(latex, rank)

    def visit_Compare(self, node: ast.Compare) -> ExprLatex:
        """Visit a comparison of two or more values."""

        rank = ranks.get_rank(node)

        left = self.visit_operand(node.left, rank)
        latex = left.latex

        for o, c in zip(node.ops, node.comparators):
            op = rules.COMPARE_OPS[type(o)]
            comparator = self.visit_operand(c, rank).latex
            latex += f"{op}{comparator}"

        return ExprLatex(latex, rank)

    def visit_Call(self, node: ast.Call) -> ExprLatex:
        """Visit a function call."""

        if config.convert_special_calls:
            special = convert_call(self, node)
            if special is not None:
                return special

        iden = helpers.get_id(node.func)

        if iden is None:
            name = self.visit(node.func).latex
        elif isinstance(node.func, ast.Attribute):
            name = self.visit_Attribute(node.func, call=True).latex
        else:
            name = formatters.format_name(iden, call=True)

        args = [self.visit(a).latex for a in node.args]

        for kw in node.keywords:
            val = self.visit(kw.value).latex
            if kw.arg is None:
                args.append("{**}" + val)
            else:
                kwarg = formatters.format_name(kw.arg)
                args.append(f"{kwarg}{rules.KWARG_ASSIGN}{val}")

        prefix, sep, suffix = rules.CALL_ARGS_SYNTAX
        arglist = formatters.format_delims(prefix, sep.join(args), suffix)

        latex = f"{name} {arglist}"
        rank = ranks.get_rank(node)

        return ExprLatex(latex, rank)

    def visit_Constant(self, node: ast.Constant) -> ExprLatex:
        """Visit a constant value."""

        latex = convert_object(node.value)

        if latex is None:
            raise RubberizeNotImplementedError(
                f"Unsupported object: {type(node.value).__name__!r}"
            )

        return latex

    def visit_Attribute(
        self, node: ast.Attribute, *, call: bool = False
    ) -> ExprLatex:
        """Visit an attribute access."""

        if (
            self.ns
            and node.attr not in config.math_constants
            and ((self.is_subst and not call) or helpers.is_unit(node, self.ns))
        ):
            obj = helpers.get_object(node, self.ns)
            latex = convert_object(obj) if obj is not None else None
            if latex is not None:
                return latex

        attr = formatters.format_name(node.attr, call=call)
        rank = ranks.get_rank(node)

        if (
            isinstance(node.value, ast.Name)
            and node.value.id in config.hidden_modules
        ):
            return ExprLatex(attr, rank)

        value_rank = ranks.get_rank(node.value)
        value = self.visit_operand(node.value, value_rank).latex

        if self.ns and helpers.is_ndarray(node, self.ns):
            latex = value + r"^{\intercal}"
        else:
            latex = f"{value}.{attr}"

        return ExprLatex(latex, rank)

    def visit_Subscript(self, node: ast.Subscript) -> ExprLatex:
        """Visit a subscript access."""

        if self.ns and self.is_subst:
            obj = helpers.get_object(node, self.ns)
            latex = convert_object(obj) if obj is not None else None
            if latex is not None:
                return latex

        name, indices = self.denest_subscripts(node)
        prefix, sep, suffix = rules.SUBSCRIPT_SYNTAX

        idx = sep.join(indices)

        if config.wrap_indices and not isinstance(node.slice, ast.Tuple):
            idx = formatters.format_delims(prefix, idx, suffix)

        if not config.use_subscripts or "_{" not in name:
            latex = name + "_{" + idx + "}"
        elif config.wrap_indices:
            latex = name + "{_{" + idx + r"}}"
        else:
            latex = name + "{_{, " + idx + r"}}"

        rank = ranks.get_rank(node)

        return ExprLatex(latex, rank)

    def visit_Starred(self, node: ast.Starred) -> ExprLatex:
        """Visit an unpacking reference (*var)."""

        latex = f"*{self.visit(node.value).latex}"
        rank = ranks.get_rank(node)

        return ExprLatex(latex, rank)

    def visit_Name(self, node: ast.Name) -> ExprLatex:
        """Visit a variable name."""

        if (
            self.ns
            and node.id not in config.math_constants
            and (self.is_subst or helpers.is_unit(node, self.ns))
        ):
            obj = helpers.get_object(node, self.ns)
            latex = convert_object(obj) if obj is not None else None
            if latex is not None:
                return latex

        latex = formatters.format_name(node.id)
        rank = ranks.get_rank(node)

        return ExprLatex(latex, rank)

    def visit_List(self, node: ast.List) -> ExprLatex:
        """Visit a list."""

        if config.show_list_as_array:
            special = self.visit_array(node)
            if special is not None:
                return special

        unpack: list[str] = []
        elts: list[str] = []

        for e in node.elts:
            if isinstance(e, ast.Starred):
                unpack.append(self.visit(e.value).latex)
            else:
                elts.append(self.visit(e).latex)

        if len(elts) > config.max_inline_elts:
            prefix, sep, suffix = rules.LIST_COL_SYNTAX
        else:
            prefix, sep, suffix = rules.LIST_ROW_SYNTAX

        latex = formatters.format_delims(prefix, sep.join(elts), suffix)

        latex = rules.UNPACKING_UNION.join([latex] + unpack)
        rank = ranks.get_rank(node)

        return ExprLatex(latex, rank)

    def visit_Tuple(self, node: ast.Tuple) -> ExprLatex:
        """Visit a tuple."""

        if config.show_tuple_as_array:
            special = self.visit_array(node)
            if special is not None:
                return special

        unpack: list[str] = []
        elts: list[str] = []

        for e in node.elts:
            if isinstance(e, ast.Starred):
                unpack.append(self.visit(e.value).latex)
            else:
                elts.append(self.visit(e).latex)

        if len(elts) > config.max_inline_elts:
            prefix, sep, suffix = rules.TUPLE_COL_SYNTAX
        else:
            prefix, sep, suffix = rules.TUPLE_ROW_SYNTAX

        latex = formatters.format_delims(prefix, sep.join(elts), suffix)

        latex = rules.UNPACKING_UNION.join([latex] + unpack)
        rank = ranks.get_rank(node)

        return ExprLatex(latex, rank)

    def visit_Slice(self, node: ast.Slice) -> ExprLatex:
        """Visit a slice (foo[1:100:2])."""

        lower = self.visit(node.lower).latex if node.lower else ""
        upper = self.visit(node.upper).latex if node.upper else ""
        step = self.visit(node.step).latex if node.step else ""
        sep = rules.SLICE_SEP

        latex = f"{lower}{sep}{upper}"

        if step:
            latex += f"{sep}{step}"

        rank = ranks.get_rank(node)

        return ExprLatex(latex, rank)

    def visit_operand(
        self,
        node: ast.expr,
        operator_rank: int,
        *,
        force: bool = False,
        non_assoc: bool = False,
    ) -> ExprLatex:
        """Visit an operand and wrap it in delimiters if needed to
        preserve the correct order of operations.

        When an operand is itself an operator with a lower rank,
        delimiters are required to indicate that it is evaluated first,
        following standard mathematical rules of precedence (PEMDAS).
        """

        operand: ExprLatex = self.visit(node)

        if (
            operand.rank < operator_rank
            or (non_assoc and operand.rank == operator_rank)
            or force
        ):
            prefix, suffix = rules.OPERAND_SYNTAX
            latex = formatters.format_delims(prefix, operand.latex, suffix)
            rank = ranks.VALUE_RANK
            return ExprLatex(latex, rank)

        return operand

    def visit_binop_operand(
        self,
        node: ast.expr,
        operator_rank: int,
        operand_rule: rules._BinOperand,
    ) -> ExprLatex:
        """Visit a binary operation's operand and apply wrapping
        depending on the supplied operand_rule.
        """

        if not operand_rule.wrap:
            return self.visit(node)
        if not isinstance(node, ast.BinOp):
            return self.visit_operand(node, operator_rank)
        if rules.BIN_OPS[type(node.op)].is_wrapped:
            return self.visit(node)
        return self.visit_operand(
            node, operator_rank, non_assoc=operand_rule.non_assoc
        )

    def visit_unit_assignment(
        self, node: ast.BinOp, magnitude: ExprLatex, units: ExprLatex
    ) -> ExprLatex:
        """Visit a unit assignment (a special type of ast.BinOp)."""

        units_node = node.right

        if isinstance(node.op, ast.Div):
            # mock-up inverse of unit (2 / ureg.mm -> 2 * ureg.mm**-1)
            units_node = ast.BinOp(
                units_node, ast.Pow(), ast.UnaryOp(ast.USub(), ast.Constant(1))
            )

        units_obj = helpers.get_object(units_node, self.ns)
        units = convert_object(units_obj) or units

        if units.latex == r"\mathrm{deg}":
            latex = magnitude.latex + r"^{\circ}"
            rank = ranks.BELOW_POW_RANK
        else:
            latex = magnitude.latex + r"\ " + units.latex
            rank = ranks.BELOW_MULT_RANK

        return ExprLatex(latex, rank)

    def visit_comprehension(self, node: ast.comprehension) -> ExprLatex:
        """Visit one `for` clause in a comprehension."""

        target = self.visit(node.target).latex
        iter_ = self.visit(node.iter).latex

        latex = target + rules.COMP_ELEMENT_OF + iter_
        ifs_latex = [self.visit(if_).latex for if_ in node.ifs]

        latex = rules.COMP_AND.join([latex] + ifs_latex)
        rank = ranks.VALUE_RANK

        return ExprLatex(latex, rank)

    def denest_subscripts(self, node: ast.Subscript) -> tuple[str, list[str]]:
        """Process subscript access such that `x[i][j][...]` becomes
        `(x, [i, j, ...])`
        """

        if isinstance(node.value, ast.Subscript):
            name, subs = self.denest_subscripts(node.value)
        else:
            name_rank = ranks.get_rank(node.value)
            name = self.visit_operand(node.value, name_rank).latex
            subs = []

        subs.append(self.visit(node.slice).latex)
        return name, subs

    def visit_array(self, node: ast.expr) -> ExprLatex | None:
        """Visit a nested list or tuple formatted as an array."""

        if not isinstance(node, (ast.List, ast.Tuple)):
            return None

        def build(node: ast.expr):
            if not isinstance(node, (ast.List, ast.Tuple)):
                part = self.visit(node)
                return None if part is None else part.latex

            parts = []

            for elt in node.elts:
                sub = build(elt)
                if sub is None:
                    return None

                parts.append(sub)

            return parts

        def shape(a):
            if not isinstance(a, list):
                return ()
            if not a:
                return (0,)

            sub = shape(a[0])
            for e in a[1:]:
                if shape(e) != sub:
                    return None

            return (len(a), *sub)

        arr = build(node)
        if arr is None:
            return None

        if shape(arr) is None:
            return None

        latex = formatters.format_array(arr)
        rank = ranks.COLLECTIONS_RANK

        return ExprLatex(latex, rank)
