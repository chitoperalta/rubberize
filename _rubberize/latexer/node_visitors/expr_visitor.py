"""Node visitor for `expr` nodes."""

import ast
from typing import Any, Optional, TYPE_CHECKING

from rubberize import exceptions
from rubberize.config import config
from rubberize.latexer.calls import convert_call
from rubberize.latexer.expr_latex import ExprLatex
from rubberize.latexer.expr_rules import (
    BOOL_OPS,
    COMPARE_OPS,
    BIN_OPS,
    UNARY_OPS,
    COLLECTIONS_ROW,
    COLLECTIONS_COL,
)
from rubberize.latexer.formatters import format_name, format_delims, format_elts
from rubberize.latexer.node_helpers import (
    get_mult_infix,
    get_object,
    is_unit_assignment,
    is_unit,
)
from rubberize.latexer.objects import convert_object
from rubberize.latexer.ranks import get_rank, BELOW_MULT_RANK, BELOW_POW_RANK

if TYPE_CHECKING:
    from rubberize.latexer.expr_rules import _BinOpdRule


# pylint: disable=invalid-name,too-many-public-methods
class ExprVisitor(ast.NodeVisitor):
    """Visitor for `expr` nodes of an AST. Each node visitor returns a
    `str`, which is the LaTeX representation for the expression.
    """

    def __init__(
        self, namespace: Optional[dict[str, Any]] = None, is_subst: bool = False
    ) -> None:
        super().__init__()
        self.namespace = namespace
        self.is_subst = is_subst

    # pylint: disable-next=useless-parent-delegation
    def visit(self, node: ast.AST) -> ExprLatex:
        """Visit a node."""
        return super().visit(node)

    def generic_visit(self, node: ast.AST) -> ExprLatex:
        """Called if no visitor method is defined for a node."""

        raise exceptions.RubberizeNotImplementedError(
            f"Unsupported expr node: {type(node).__name__!r}"
        )

    def visit_BoolOp(self, node: ast.BoolOp) -> ExprLatex:
        """Visit a boolean `or` or `and` operation.

        Note that `not` is considered a unary operator so it is handled
        by `visit_UnaryOp()`.
        """

        rank = get_rank(node)

        op_latex = BOOL_OPS[type(node.op)]
        values_latex = [self.visit_opd(o, rank).latex for o in node.values]

        if len(values_latex) > 2:
            latex = format_elts(
                values_latex,
                r" \\" + "\n" + rf"\displaystyle {op_latex}\ ",
                (
                    r"\left\{" + "\n" + r"\begin{array}{l}",
                    r"\end{array}" + "\n" + r"\right\}",
                ),
            )
        else:
            latex = op_latex.join(values_latex)

        return ExprLatex(latex, rank)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> ExprLatex:
        """Visit a named expression such as `foo := 42`, which is an
        in-place assignment operation.
        """

        rank = get_rank(node)

        op_latex = r" \gets "
        target_latex = format_name(node.target.id)
        value = self.visit_opd(node.value, rank)
        latex = target_latex + op_latex + value.latex

        return ExprLatex(latex, rank)

    def visit_BinOp(self, node: ast.BinOp) -> ExprLatex:
        """Visit a binary operation (like addition or division)."""

        rank = get_rank(node)

        op = BIN_OPS[type(node.op)]
        left = self.visit_binop_opd(node.left, rank, op.left)
        right = self.visit_binop_opd(node.right, rank, op.right)

        if is_unit_assignment(node, self.namespace):
            return self.visit_unit_assign(node, left, right)

        if (
            isinstance(node.op, ast.Pow)
            and isinstance(node.left, ast.Name)
            and ("^" in left.latex or "_{" in left.latex)
        ):
            left.latex = f"{{{left.latex}}}"

        if config.use_contextual_mult and isinstance(node.op, ast.Mult):
            infix = get_mult_infix(node, left.latex, right.latex)
            latex = op.prefix + left.latex + infix + right.latex + op.suffix
        else:
            latex = op.prefix + left.latex + op.infix + right.latex + op.suffix

        return ExprLatex(latex, rank)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ExprLatex:
        """Visit a unary operation."""

        rank = get_rank(node)

        op_latex = UNARY_OPS[type(node.op)]
        opd = self.visit_opd(node.operand, rank, non_assoc=True)
        latex = op_latex + opd.latex

        return ExprLatex(latex, rank)

    def visit_Lambda(self, node: ast.Lambda) -> ExprLatex:
        """Visit an lambda expression, which is an anonymous function
        assignment operation.
        """

        rank = get_rank(node)

        op_latex = r" \mapsto "
        args_latex = r",\, ".join(format_name(a.arg) for a in node.args.args)
        body = self.visit_opd(node.body, rank)
        latex = args_latex + op_latex + body.latex

        return ExprLatex(latex, rank)

    def visit_IfExp(self, node: ast.IfExp) -> ExprLatex:
        """Visit a ternary expression such as `a if b else c`."""

        rank = get_rank(node)
        cur_node: ast.expr = node

        if self.is_subst and self.namespace:
            while isinstance(cur_node, ast.IfExp):
                if get_object(cur_node.test, self.namespace):
                    return self.visit(cur_node.body)
                cur_node = cur_node.orelse
            return self.visit(cur_node)

        cur_latex = ""
        while isinstance(cur_node, ast.IfExp):
            body = self.visit(cur_node.body)
            test = self.visit(cur_node.test)
            cur_latex += (
                rf"\displaystyle {body.latex}, &\text{{if}}\ {test.latex} \\ "
            )
            cur_node = cur_node.orelse
        orelse = self.visit(cur_node)
        cur_latex += rf"\displaystyle {orelse.latex}, &\text{{otherwise}}"

        latex = rf"\begin{{cases}} {cur_latex} \end{{cases}}"

        return ExprLatex(latex, rank)

    def visit_Dict(self, node: ast.Dict) -> ExprLatex:
        """Visit a dictionary."""

        rank = get_rank(node)

        if not node.keys:
            return ExprLatex(r"\left\{\right\}", rank)

        dict_latex = {}
        unpack_latex = []
        for key, value in zip(node.keys, node.values):
            if key is None:
                unpack_latex.append(self.visit(value).latex)
            else:
                dict_latex[self.visit(key).latex] = self.visit(value).latex

        if config.show_dict_as_col:
            elts = [rf"{k} &\to {v}" for k, v in dict_latex.items()]
            syntax = COLLECTIONS_COL[dict]
        else:
            elts = [rf"{k} \to {v}" for k, v in dict_latex.items()]
            syntax = COLLECTIONS_ROW[dict]
        dict_latex = format_elts(elts, *syntax)

        latex = r" \cup ".join([dict_latex] + unpack_latex)

        return ExprLatex(latex, rank)

    def visit_Set(self, node: ast.Set) -> ExprLatex:
        """Visit a set."""

        rank = get_rank(node)

        elts_latex = sorted(self.visit(e).latex for e in node.elts)
        if config.show_set_as_col:
            syntax = COLLECTIONS_COL[set]
        else:
            syntax = COLLECTIONS_ROW[set]
        latex = format_elts(elts_latex, *syntax)

        return ExprLatex(latex, rank)

    def visit_ListComp(self, node: ast.ListComp) -> ExprLatex:
        """Visit a list comprehension."""

        rank = get_rank(node)

        elt = self.visit(node.elt)
        comps_latex = r",\, ".join(self.visit(c).latex for c in node.generators)
        latex = format_delims(
            rf"{elt.latex} \;\middle|\; {comps_latex}",
            (r"\left(\,", r"\,\right)"),
        )

        return ExprLatex(latex, rank)

    def visit_SetComp(self, node: ast.SetComp) -> ExprLatex:
        """Visit a set comprehension."""

        rank = get_rank(node)

        elt = self.visit(node.elt)
        comps_latex = r",\, ".join(self.visit(c).latex for c in node.generators)
        latex = format_delims(
            rf"{elt.latex} \;\middle|\; {comps_latex}",
            (r"\left\{\, ", r" \,\right\}"),
        )

        return ExprLatex(latex, rank)

    def visit_DictComp(self, node: ast.DictComp) -> ExprLatex:
        """Visit a set comprehension."""

        rank = get_rank(node)

        key = self.visit(node.key)
        value = self.visit(node.value)
        elt_latex = key.latex + r" \mapsto " + value.latex

        comps_latex = r",\, ".join(self.visit(c).latex for c in node.generators)
        latex = format_delims(
            elt_latex + r" \;\middle|\; " + comps_latex,
            (r"\left\{\,", r"\,\right\}"),
        )

        return ExprLatex(latex, rank)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> ExprLatex:
        """Visit a generator expression."""

        rank = get_rank(node)

        elt = self.visit(node.elt)
        comps_latex = r",\, ".join(self.visit(c).latex for c in node.generators)
        latex = rf"{elt.latex} \;\middle|\; {comps_latex}"

        return ExprLatex(latex, rank)

    def visit_Compare(self, node: ast.Compare) -> ExprLatex:
        """Visit a comparison of two or more values."""

        rank = get_rank(node)

        left = self.visit_opd(node.left, rank)
        latex = left.latex
        for node_op, node_opd in zip(node.ops, node.comparators):
            op_latex = COMPARE_OPS[type(node_op)]
            opd = self.visit_opd(node_opd, rank)
            latex += f" {op_latex} {opd.latex}"

        return ExprLatex(latex, rank)

    def visit_Call(self, node: ast.Call) -> ExprLatex:
        """Visit a function call."""

        return convert_call(self, node)

    def visit_Constant(self, node: ast.Constant) -> ExprLatex:
        """Visit a constant value."""

        object_latex = convert_object(node.value)
        if object_latex is not None:
            return object_latex

        raise exceptions.RubberizeNotImplementedError(
            f"Unsupported Constant type: {type(node.value).__name__!r}"
        )

    def visit_Attribute(self, node: ast.Attribute, *, call=False) -> ExprLatex:
        """Visit an attribute access."""

        rank = get_rank(node)

        if (
            self.namespace
            and node.attr not in config.math_constants
            and ((self.is_subst and not call) or is_unit(node, self.namespace))
        ):
            obj = get_object(node, self.namespace)
            obj_latex = convert_object(obj) if obj is not None else None
            if obj_latex is not None:
                return obj_latex

        attr_latex = format_name(node.attr, call=call)
        if (
            isinstance(node.value, ast.Name)
            and node.value.id in config.hidden_modules
        ):
            return ExprLatex(attr_latex, rank)

        value = self.visit(node.value)
        latex = f"{value.latex}.{attr_latex}"

        return ExprLatex(latex, rank)

    def visit_Subscript(self, node: ast.Subscript) -> ExprLatex:
        """Visit a subscript access, such as `foo[1]`."""

        rank = get_rank(node)

        if self.is_subst and self.namespace:
            obj = get_object(node, self.namespace)
            obj_latex = convert_object(obj) if obj is not None else None
            if obj_latex is not None:
                return obj_latex

        name_latex, indices = self.denest_subscripts(node)

        if config.wrap_indices and not isinstance(node.slice, ast.Tuple):
            indices_latex = format_delims(
                r",\, ".join(indices), (r"\left(", r"\right)")
            )
        else:
            indices_latex = ", ".join(indices)

        if not config.use_subscripts or "_{" not in name_latex:
            latex = name_latex + "_{" + indices_latex + "}"
        elif config.wrap_indices:
            latex = name_latex + "{_{" + indices_latex + r"}}"
        else:
            latex = name_latex + "{_{, " + indices_latex + r"}}"

        return ExprLatex(latex, rank)

    def visit_Starred(self, node: ast.Starred) -> ExprLatex:
        """Visit a `*var` variable reference."""

        rank = get_rank(node)

        if self.is_subst and self.namespace:
            return self.visit(node.value)

        latex = f"*{self.visit(node.value)}"

        return ExprLatex(latex, rank)

    def visit_Name(self, node: ast.Name) -> ExprLatex:
        """Visit a variable name."""

        rank = get_rank(node)

        if (
            self.namespace
            and node.id not in config.math_constants
            and (self.is_subst or is_unit(node, self.namespace))
        ):
            obj = get_object(node, self.namespace)
            obj_latex = convert_object(obj) if obj is not None else None
            if obj_latex is not None:
                return obj_latex

        latex = format_name(node.id)

        return ExprLatex(latex, rank)

    def visit_List(self, node: ast.List) -> ExprLatex:
        """Visit a list."""

        rank = get_rank(node)

        elts_latex = [self.visit(e).latex for e in node.elts]
        if config.show_list_as_col:
            syntax = COLLECTIONS_COL[list]
        else:
            syntax = COLLECTIONS_ROW[list]
        latex = format_elts(elts_latex, *syntax)

        return ExprLatex(latex, rank)

    def visit_Tuple(self, node: ast.Tuple) -> ExprLatex:
        """Visit a tuple."""

        rank = get_rank(node)

        elts_latex = [self.visit(e).latex for e in node.elts]
        if config.show_tuple_as_col:
            syntax = COLLECTIONS_COL[tuple]
        else:
            syntax = COLLECTIONS_ROW[tuple]
        latex = format_elts(elts_latex, *syntax)

        return ExprLatex(latex, rank)

    def visit_Slice(self, node: ast.Slice) -> ExprLatex:
        """Visit a slicing part of subscript, such as `foo[1:100:2]`."""

        rank = get_rank(node)

        lower_latex = self.visit(node.lower).latex if node.lower else ""
        upper_latex = self.visit(node.upper).latex if node.upper else ""
        step_latex = self.visit(node.step).latex if node.step else ""

        if step_latex:
            latex = lower_latex + " : " + upper_latex + " : " + step_latex
        else:
            latex = lower_latex + " : " + upper_latex

        return ExprLatex(latex, rank)

    def visit_opd(
        self,
        opd_node: ast.expr,
        op_rank: int,
        *,
        force: bool = False,
        non_assoc: bool = False,
    ) -> ExprLatex:
        """Visit an operator's operand and wrap it in parenthesis if
        needed to preserve the correct order of operations.

        When an operand is itself an operator with a lower rank,
        parentheses are required to indicate that it is evaluated first.
        This follows standard mathematical rules of precedence (e.g.,
        PEMDAS).
        """

        opd: ExprLatex = self.visit(opd_node)

        if opd.rank < op_rank or (non_assoc and opd.rank == op_rank) or force:
            return ExprLatex(format_delims(opd.latex, (r"\left(", r"\right)")))
        return opd

    def visit_binop_opd(
        self, opd_node: ast.expr, op_rank: int, opd_rule: "_BinOpdRule"
    ) -> ExprLatex:
        """Visit a binary operator's operand and apply wrapping rules
        depending on the supplied rules.
        """

        if not opd_rule.wrap:
            return self.visit(opd_node)
        if not isinstance(opd_node, ast.BinOp):
            return self.visit_opd(opd_node, op_rank)
        if BIN_OPS[type(opd_node.op)].is_wrapped:
            return self.visit(opd_node)
        return self.visit_opd(opd_node, op_rank, non_assoc=opd_rule.non_assoc)

    def visit_unit_assign(
        self, node: ast.BinOp, value: ExprLatex, unit: ExprLatex
    ) -> ExprLatex:
        """Visit a unit assignment, which is a special type of a mult
        operation.
        """

        rank = BELOW_MULT_RANK
        circ_rank = BELOW_POW_RANK

        unit_node = node.right
        if isinstance(node.op, ast.Div):
            # get inverse of the unit
            unit_node = ast.BinOp(
                left=unit_node,
                op=ast.Pow(),
                right=ast.UnaryOp(op=ast.USub(), operand=ast.Constant(1)),
            )
        unit_obj = get_object(unit_node, self.namespace)
        unit = convert_object(unit_obj) or unit

        if unit.latex == r"\mathrm{deg}":
            latex = value.latex + r"^{\circ}"
            return ExprLatex(latex, circ_rank)

        latex = value.latex + r"\ " + unit.latex
        return ExprLatex(latex, rank)

    def visit_comprehension(self, node: ast.comprehension) -> ExprLatex:
        """Visit one `for` clause in a comprehension."""

        target = self.visit(node.target)
        iter_ = self.visit(node.iter)
        comp_latex = target.latex + r" \in " + iter_.latex
        ifs_latex = [self.visit(if_).latex for if_ in node.ifs]
        return ExprLatex(r" \land ".join([comp_latex] + ifs_latex))

    def denest_subscripts(self, node: ast.Subscript) -> tuple[str, list[str]]:
        """Process subscript access such that `x[i][j][...]` becomes
        `(x, [i, j, ...])`
        """

        if isinstance(node.value, ast.Subscript):
            name_latex, subs_latex = self.denest_subscripts(node.value)
        else:
            name_latex = self.visit(node.value).latex
            subs_latex = []

        subs_latex.append(self.visit(node.slice).latex)
        return name_latex, subs_latex
