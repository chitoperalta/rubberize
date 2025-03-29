"""Node visitor for `stmt` nodes."""

import ast
from typing import Optional, Any

import rubberize.vendor.ast_comments as ast_c

from rubberize import exceptions
from rubberize.config import config
from rubberize.latexer.components.calcsheet import (
    CalcSheet,
    convert_check_method,
    convert_conclude_method,
    convert_calc_sheet,
)
from rubberize.latexer.components.table import (
    Table,
    convert_table,
)
from rubberize.latexer.expr_modes import (
    definition,
    substitution,
    result,
    all_modes,
)
from rubberize.latexer.formatters import (
    format_equation,
    format_name,
    format_elts,
)
from rubberize.latexer.stmt_latex import StmtLatex
from rubberize.latexer.node_helpers import (
    get_arg_ids,
    get_desc_and_over,
    get_object,
    get_target_ids,
    is_class,
    is_method,
    is_piecewise_functiondef,
    is_uniform_assign_if,
    strip_docstring,
    strip_body_comments,
)


# pylint: disable=invalid-name
class StmtVisitor(ast.NodeVisitor):
    """Visitor for `stmt` nodes of an AST.

    Each node visitor returns a `StmtLatex` for the node, which is a
    formatted LaTeX representation (and any text description) for the
    statement and its children statements, if any.
    """

    def __init__(self, namespace: Optional[dict[str, Any]] = None) -> None:
        super().__init__()
        self.namespace = namespace

    # pylint: disable-next=useless-parent-delegation
    def visit(self, node: ast.AST) -> StmtLatex:
        """Visit a node."""
        return super().visit(node)

    def generic_visit(self, node: ast.AST) -> StmtLatex:
        """Called if no visitor method is defined for a node."""

        raise exceptions.RubberizeNotImplementedError(
            f"Unsupported stmt node: {type(node).__name__!r}"
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> StmtLatex:
        """Visit a function definition node."""

        node = strip_docstring(node)

        # Remove arguments and assignments from namespace copy
        func_ns = self.namespace.copy() if self.namespace else {}
        for iden in get_arg_ids(node.args) | get_target_ids(node.body):
            func_ns.pop(iden, None)

        # Special formats:
        if is_piecewise_functiondef(node):
            return self.visit_piecewise_functiondef(node, func_ns)

        body = node.body

        if isinstance(body[0], ast_c.Comment):
            # FunctionDef inline comment is stored as first item in body
            description, override = get_desc_and_over(body[0])
            if "hide" in override:
                return StmtLatex(None, description)
            body = body[1:]
        else:
            description, override = None, {}

        with config.override(**override):
            name = format_name(node.name, call=True)
            args = self.visit_arguments(node.args)

            if body and isinstance(body[-1], ast.Return) and body[-1].value:
                ret = " = ".join(all_modes(body[-1].value, func_ns))
                body = body[:-1]
            else:
                ret = r"\emptyset"

            stmt_latex = StmtLatex(name + " " + args + " = " + ret)
            stmt_latex.body = StmtVisitor(func_ns).loop_body(body)

        if stmt_latex.body and isinstance(stmt_latex.latex, str):
            stmt_latex.latex += r"\ \text{where:}"
        if description:
            stmt_latex.desc = description
        return stmt_latex

    def visit_Return(self, node: ast.Return) -> StmtLatex:
        """Visit a return statement.

        The return statement must only appear at the end of a function
        definition. In which case, the return statement is handled by
        visit_FunctionDef().
        """

        raise exceptions.RubberizeSyntaxError(
            "`Return` must only appear at the end of a function definiton "
            "or a piecewise function definition."
        )

    def visit_Assign(self, node: ast.Assign) -> StmtLatex:
        """Visit an assignment such as `a = 1`."""

        description, override = get_desc_and_over(node)
        if "hide" in override:
            return StmtLatex(None, description)

        with config.override(**override):
            if self.namespace:
                if is_class(node.value, CalcSheet, self.namespace):
                    return convert_calc_sheet(node.value, self.namespace)
                if is_class(node.value, Table, self.namespace):
                    return convert_table(node.value, self.namespace)

            lhs = self.visit_assign_targets(node.targets)
            rhs = all_modes(node.value, self.namespace, node.targets[0])
            stmt_latex = StmtLatex(format_equation(lhs, rhs))

        if description:
            stmt_latex.desc = description
        return stmt_latex

    def visit_AnnAssign(self, node: ast.AnnAssign) -> StmtLatex:
        """Visit an annotated assignment.

        Annotations are stripped so the return is like an assignment or
        an expression statement.
        """

        description, override = get_desc_and_over(node)
        if "hide" in override:
            return StmtLatex(None, description)

        with config.override(**override):
            lhs = definition(node.target, self.namespace)
            if node.value:
                rhs = all_modes(node.value, self.namespace, node.target)
            elif self.namespace:
                rhs = result(node.target, self.namespace)
            else:
                rhs = None
            stmt_latex = StmtLatex(format_equation(lhs, rhs))

        if description:
            stmt_latex.desc = description
        return stmt_latex

    # pylint: disable-next=too-many-return-statements
    def visit_If(self, node: ast.If) -> StmtLatex:
        """Visit an `if` statement."""

        cur: ast.stmt = node

        # if not config.show_substitution:
        #     # Use special formats if possible
        #     if is_uniform_assign_if(node):
        #         return self.visit_uniform_assign_if(node)
        #     if not config.show_result or not self.namespace:
        #         return self.visit_definition_if(node)

        while isinstance(cur, ast.If):
            # Inline comment for ast.If is in the test attribute, weirdly
            cur_desc, cur_over = get_desc_and_over(cur.test)
            if "hide" in cur_over:
                return StmtLatex(None, cur_desc)

            with config.override(**cur_over):
                test_cond = get_object(cur.test, self.namespace)

                if test_cond is None or not config.show_substitution:
                    # Fallback to special formats if no object for test
                    if is_uniform_assign_if(node):
                        return self.visit_uniform_assign_if(node)
                    return self.visit_definition_if(node)

                if test_cond:
                    test = definition(cur.test, self.namespace)

                    if config.show_substitution:
                        test_sub = substitution(cur.test, self.namespace)
                        if test != test_sub and not (
                            isinstance(cur.test, ast.Compare)
                            and len(cur.test.ops) == 1
                            and isinstance(cur.test.ops[0], ast.Eq)
                        ):
                            test += r"\ \to\ " + test_sub

                    if len(cur.body) == 1 and isinstance(cur.body[0], ast.Pass):
                        cur_latex = StmtLatex(None)
                    else:
                        cur_latex = StmtLatex(
                            rf"\text{{Since}}\ {test} \text{{:}}"
                        )
                        cur_latex.body = self.loop_body(cur.body)

                    if cur_desc:
                        cur_latex.desc = cur_desc

                    return cur_latex

            if len(cur.orelse) > 1:
                # An `else` block.
                else_body = cur.orelse
                if isinstance(else_body[0], ast_c.Comment):
                    else_desc, else_over = get_desc_and_over(else_body[0])
                    if "hide" in else_over:
                        return StmtLatex(None, else_desc)
                    else_body = else_body[1:]
                else:
                    else_desc, else_over = None, {}

                with config.override(**else_over):
                    else_latex = StmtLatex(None)
                    else_latex.body = self.loop_body(else_body)
                    if else_desc:
                        else_latex.desc = else_desc
                    return else_latex

            if len(cur.orelse) == 1:
                # Either an `elif` block or a single statement `else`.
                cur = cur.orelse[0]
            else:
                return StmtLatex(None)

        else_latex = StmtLatex(None)
        else_latex.body = [self.visit(cur)]

        return else_latex

    def visit_Import(self, node: ast.Import) -> StmtLatex:
        """Visit an `import` statement."""

        description, _ = get_desc_and_over(node)
        return StmtLatex(None, description)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> StmtLatex:
        """Visit a `from x import y` statement."""

        description, _ = get_desc_and_over(node)
        return StmtLatex(None, description)

    def visit_Expr(self, node: ast.Expr) -> StmtLatex:
        """Visit an expression that is written as a statement, i.e. the
        expression appears by itself with its return value not used or
        stored.
        """

        description, override = get_desc_and_over(node)
        if "hide" in override:
            return StmtLatex(None, description)

        with config.override(**override):
            if self.namespace:
                if is_class(node.value, CalcSheet, self.namespace):
                    return convert_calc_sheet(node.value, self.namespace)
                if is_method(node.value, CalcSheet, "check", self.namespace):
                    return convert_check_method(node.value, self.namespace)
                if is_method(node.value, CalcSheet, "conclude", self.namespace):
                    return convert_conclude_method(node.value, self.namespace)
                if is_class(node.value, Table, self.namespace):
                    return convert_table(node.value, self.namespace)

            display_modes = all_modes(node.value, self.namespace)
            if display_modes:
                lhs, *rhs = all_modes(node.value, self.namespace)
                stmt_latex = StmtLatex(format_equation(lhs, rhs))
            else:
                stmt_latex = StmtLatex(None)

        if description:
            stmt_latex.desc = description
        return stmt_latex

    def visit_Pass(self, node: ast.Pass) -> StmtLatex:
        """Visit a `pass` statement."""

        description, _ = get_desc_and_over(node)
        return StmtLatex(None, description)

    def visit_arguments(self, node: ast.arguments) -> str:
        """Visit the arguments of a function definition."""

        n_pos_defs = len(node.defaults) - len(node.args)
        if n_pos_defs > 0:
            pos_defs_pad = len(node.posonlyargs) - n_pos_defs
            pos_defs = [None] * pos_defs_pad + node.defaults[:n_pos_defs]
            defaults = node.defaults[n_pos_defs:]
        else:
            defaults_pad = len(node.args) - len(node.defaults)
            pos_defs = []
            defaults = [None] * defaults_pad + node.defaults

        args_latex = []
        for posonlyarg, pos_def in zip(node.posonlyargs, pos_defs):
            args_latex.append(self.visit_arg(posonlyarg, pos_def))
        for arg, default in zip(node.args, defaults):
            args_latex.append(self.visit_arg(arg, default))
        if node.vararg:
            args_latex.append("*" + self.visit_arg(node.vararg))
        for kwonlyarg, kw_default in zip(node.kwonlyargs, node.kw_defaults):
            args_latex.append(self.visit_arg(kwonlyarg, kw_default))
        if node.kwarg:
            args_latex.append("**" + self.visit_arg(node.kwarg))

        return format_elts(args_latex, r",\, ", (r"\left(", r"\right)"))

    def visit_arg(
        self, node: ast.arg, default: Optional[ast.expr] = None
    ) -> str:
        """Visit an argument of a function definition."""

        arg_latex = format_name(node.arg)
        if default:
            default_latex = definition(default, self.namespace)
            return arg_latex + r" \leftarrow " + default_latex
        return arg_latex

    def visit_piecewise_functiondef(
        self, node: ast.FunctionDef, func_ns: dict[str, Any]
    ) -> StmtLatex:
        """Visit a piecewise function definition.

        For example:
            def sgn(x):
                if x > 1:
                    return 1
                if x < 1:
                    return -1
                return 0
        """

        # Only the description on function definition is used
        description, override = get_desc_and_over(node.body[0])
        if "hide" in override:
            return StmtLatex(None, description)

        # Remove all func body comments
        func_body = strip_body_comments(node.body)

        with config.override(**override):
            name = format_name(node.name, call=True)
            args = self.visit_arguments(node.args)

            defs: list[str] = []
            subs: list[str] = []

            for stmt in func_body:
                assert isinstance(stmt, ast.If | ast.Return)

                cur: ast.If | ast.Return = stmt

                while isinstance(cur, ast.If):
                    _, cur_over = get_desc_and_over(cur.test)

                    body = strip_body_comments(cur.body)
                    orelse = strip_body_comments(cur.orelse)

                    assert len(body) == 1
                    assert isinstance(body[0], ast.Return)
                    assert len(orelse) < 2

                    if "hide" not in cur_over:
                        with config.override(**cur_over):
                            ret = body[0]
                            _, ret_over = get_desc_and_over(ret)

                            assert ret.value is not None

                            with config.override(**ret_over):
                                value = definition(ret.value, func_ns)
                                sub = substitution(ret.value, func_ns)
                                test = definition(cur.test, func_ns)

                        defs.append(
                            rf"\displaystyle {value}, &\text{{if}}\ {test}"
                        )
                        subs.append(
                            rf"\displaystyle {sub}, &\text{{if}}\ {test}"
                        )

                    if not orelse:
                        break

                    assert isinstance(orelse[0], (ast.If, ast.Return))

                    cur = orelse[0]

                if isinstance(cur, ast.Return) and cur.value:
                    _, cur_over = get_desc_and_over(cur)

                    if "hide" not in cur_over:
                        with config.override(**cur_over):
                            value = definition(cur.value, func_ns)
                            sub = substitution(cur.value, func_ns)

                        defs.append(
                            rf"\displaystyle {value}, &\text{{otherwise}}"
                        )
                        subs.append(
                            rf"\displaystyle {sub}, &\text{{otherwise}}"
                        )

            defs_latex = format_elts(
                defs, r" \\ ", (r"\begin{cases}", r"\end{cases}")
            )
            subs_latex = format_elts(
                subs, r" \\ ", (r"\begin{cases}", r"\end{cases}")
            )

            rhs = [defs_latex]
            if config.show_substitution and subs_latex not in rhs:
                rhs.append(subs_latex)

            stmt_latex = StmtLatex(format_equation(name + " " + args, rhs))

        if description:
            stmt_latex.desc = description

        return stmt_latex

    def visit_assign_targets(self, targets: list[ast.expr]) -> list[str]:
        """Visit an assignment target(s)."""

        lhs = []
        for target in targets:
            if isinstance(target, ast.Tuple):
                # We don't want parentheses in the tuple
                elts = [definition(e, self.namespace) for e in target.elts]
                lhs.append(r",\, ".join(elts))
            else:
                lhs.append(definition(target, self.namespace))

        return lhs

    def visit_uniform_assign_if(self, node: ast.If) -> StmtLatex:
        """Visit an `if`-`elif`-`else` ladder that has the same
        assignment targets in each its branches.

        For example:
            if x < a:
                y = x + a
            elif x > a:
                y = x - a
            else:
                y = x
        """

        # Only the description on the first assignment comment is used.
        description, _ = get_desc_and_over(node.body[0])

        cur: ast.If | ast.Assign = node
        lhs: list[str] = []
        defs: list[str] = []
        subs: list[str] = []
        res: str = ""

        while isinstance(cur, ast.If):
            _, cur_over = get_desc_and_over(cur.test)

            body = strip_body_comments(cur.body)
            orelse = strip_body_comments(cur.orelse)

            # These assertions are checked by is_uniform_assign_if()
            assert len(body) == 1
            assert isinstance(body[0], ast.Assign)
            assert len(orelse) < 2

            if "hide" not in cur_over:
                with config.override(**cur_over):
                    assign = body[0]
                    _, ass_over = get_desc_and_over(assign)

                    with config.override(**ass_over):
                        if not lhs:
                            lhs = self.visit_assign_targets(assign.targets)
                            if self.namespace:
                                res = result(assign.targets[0], self.namespace)

                        value = definition(assign.value, self.namespace)
                        sub = substitution(assign.value, self.namespace)
                        test = definition(cur.test, self.namespace)

                defs.append(rf"\displaystyle {value}, &\text{{if}}\ {test}")
                subs.append(rf"\displaystyle {sub}, &\text{{if}}\ {test}")

            if not orelse:
                break

            assert isinstance(orelse[0], (ast.If, ast.Assign))

            cur = orelse[0]

        if isinstance(cur, ast.Assign):
            _, cur_over = get_desc_and_over(cur)

            if "hide" not in cur_over:
                with config.override(**cur_over):
                    value = definition(cur.value, self.namespace)
                    sub = substitution(cur.value, self.namespace)

                defs.append(rf"\displaystyle {value}, &\text{{otherwise}}")
                subs.append(rf"\displaystyle {sub}, &\text{{otherwise}}")

        defs_latex = format_elts(
            defs, r" \\ ", (r"\begin{cases}", r"\end{cases}")
        )
        subs_latex = format_elts(
            subs, r" \\ ", (r"\begin{cases}", r"\end{cases}")
        )

        rhs = []
        if config.show_definition:
            rhs.append(defs_latex)
        if config.show_substitution and subs_latex not in rhs:
            rhs.append(subs_latex)
        if config.show_result:
            rhs.append(res)

        stmt_latex = StmtLatex(format_equation(lhs, rhs))

        if description:
            stmt_latex.desc = description

        return stmt_latex

    def visit_definition_if(self, node: ast.If) -> StmtLatex:
        """Visit an `if` statement and show all its conditions, without
        substitution.
        """

        cur: ast.stmt = node
        conds_latex: list[StmtLatex] = []

        while isinstance(cur, ast.If):
            cur_desc, cur_over = get_desc_and_over(cur.test)

            if "hide" not in cur_over:
                with config.override(**cur_over):
                    test = definition(cur.test, self.namespace)
                    if_ = "If" if not conds_latex else "Else, if"

                    cur_latex = StmtLatex(rf"\text{{{if_}}}\ {test} \text{{:}}")
                    cur_latex.body = self.loop_body(cur.body)

                if cur_desc:
                    cur_latex.desc = cur_desc

                conds_latex.append(cur_latex)

            if len(cur.orelse) > 1:
                # An `else` block.
                else_body = cur.orelse
                if isinstance(else_body[0], ast_c.Comment):
                    else_desc, else_over = get_desc_and_over(else_body[0])
                    else_body = else_body[1:]
                else:
                    else_desc, else_over = None, {}

                if "hide" not in else_over:
                    with config.override(**else_over):
                        else_latex = StmtLatex(r"\text{Otherwise:}")
                        else_latex.body = self.loop_body(else_body)

                    if else_desc:
                        else_latex.desc = else_desc

                    conds_latex.append(else_latex)

            if len(cur.orelse) == 1:
                # Either and `elif` or a single statement for `else`.
                cur = cur.orelse[0]
            else:
                return StmtLatex(None, body=conds_latex)

        else_latex = StmtLatex(r"\text{Otherwise:}")
        else_latex.body = [self.visit(cur)]
        conds_latex.append(else_latex)

        return StmtLatex(None, body=conds_latex)

    def loop_body(self, body: list[ast.stmt]) -> list["StmtLatex"]:
        """Visit each statement in a statement body."""

        body_latex: list[StmtLatex] = []
        comment_block: list[str] = []
        overrides: dict[str, Any] = {}
        hide: bool = False

        for stmt in body:
            if isinstance(stmt, ast_c.Comment):
                description, override = get_desc_and_over(stmt)
                if "hide" in override:
                    hide = True
                elif "endhide" in override:
                    hide = False
                else:
                    if comment_block:
                        overrides.update(override)
                    else:
                        overrides = override
                    comment_block.append(description or "")

            elif not hide:
                if comment_block:
                    # Non-comment statement; flush comment block
                    body_latex.append(StmtLatex(None, "\n".join(comment_block)))
                    comment_block.clear()

                with config.override(**overrides):
                    body_latex.append(self.visit(stmt))

        if comment_block:
            body_latex.append(StmtLatex(None, "\n".join(comment_block)))

        return body_latex
