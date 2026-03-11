"""Node visitor for stmt nodes."""

import ast
from typing import TYPE_CHECKING

from rubberize._exceptions import (
    RubberizeNotImplementedError,
    RubberizeSyntaxError,
)
from rubberize.config import config
from rubberize.latexer import displays, formatters, helpers, rules
from rubberize.latexer.blocks import convert_block
from rubberize.latexer.stmt_latex import StmtLatex
import rubberize.vendor.ast_comments as ast_c

if TYPE_CHECKING:
    from typing import Iterable


# pylint: disable=invalid-name
class StmtVisitor(ast.NodeVisitor):
    """Node visitor for ast.stmt nodes.

    Each visitor method returns a StmtLatex for the node.
    """

    def __init__(self, ns: dict[str, object] | None = None) -> None:
        super().__init__()
        self.ns = ns

    # pylint: disable-next=useless-parent-delegation
    def visit(self, node: ast.AST) -> StmtLatex:
        return super().visit(node)

    def generic_visit(self, node: ast.AST) -> StmtLatex:
        """Called if no visitor method is defined for a node."""

        raise RubberizeNotImplementedError(
            f"Unsupported ast.stmt node: {type(node).__name__!r}"
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> StmtLatex:
        """Visit a function definition node."""

        node = helpers.strip_docstring(node)
        ns = self.ns.copy() if self.ns else {}

        arg_ids = helpers.get_arg_ids(node.args)
        body_ids = helpers.get_target_ids(node.body)

        for iden in arg_ids | body_ids:
            ns.pop(iden, None)

        if helpers.is_piecewise_funcdef(node):
            return self.visit_piecewise_funcdef(node, ns=ns)

        body = node.body

        if isinstance(body[0], ast_c.Comment):
            # inline comment is stored as first item in ast.FunctionDef body
            desc, cfg = helpers.get_desc(node)
            if "hide" in cfg:
                return StmtLatex(None, desc)

            body = body[1:]
        else:
            desc, cfg = None, {}

        with config.override(**cfg):
            name = formatters.format_name(node.name, call=True)
            args = self.visit_arguments(node.args)

            if body and isinstance(body[-1], ast.Return) and body[-1].value:
                ret = " = ".join(displays.all_modes(body[-1].value, ns))
                body = body[:-1]
            else:
                ret = r"\emptyset"

            latex = f"{name} {args} = {ret}"
            latex_body = StmtVisitor(ns).visit_body(body)

        if latex_body:
            latex += r"\ \text{where:}"

        return StmtLatex(latex, desc, latex_body)

    def visit_Return(self, node: ast.Return) -> StmtLatex:
        """Visit a return statement."""

        raise RubberizeSyntaxError(
            "return must only appear at the end of a function definiton "
            "or in a piecewise function definition."
        )

    def visit_Assign(self, node: ast.Assign) -> StmtLatex:
        """Visit an assignment (such as foo = 42)."""

        desc, cfg = helpers.get_desc(node)
        if "hide" in cfg:
            return StmtLatex(None, desc)

        with config.override(**cfg):
            if self.ns:
                special = convert_block(node, self.ns)
                if special is not None:
                    return special

            lhs = self.visit_assign_targets(node.targets)
            rhs = displays.all_modes(node.value, self.ns, node.targets[0])
            latex = formatters.format_equation(lhs, rhs)

        return StmtLatex(latex, desc)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> StmtLatex:
        """Visit an annotated assignment.

        Annotations are stripped so the rendered LaTeX is like an
        ast.Assign or ast.Expr
        """

        desc, cfg = helpers.get_desc(node)
        if "hide" in cfg:
            return StmtLatex(None, desc)

        with config.override(**cfg):
            if self.ns:
                special = convert_block(node, self.ns)
                if special is not None:
                    return special

            lhs = displays.definition(node.target, self.ns)

            if node.value:
                rhs = displays.all_modes(node.value, self.ns, node.target)
            elif self.ns:
                rhs = displays.result(node.target, self.ns)
            else:
                rhs = None

        latex = formatters.format_equation(lhs, rhs)

        return StmtLatex(latex, desc)

    # pylint: disable-next=too-many-return-statements,too-many-branches
    def visit_If(self, node: ast.If) -> StmtLatex:
        """Visit an If (if-elif-else ladder).

        Rendering of an else branch is a headless StmtLatex.
        """

        cur: ast.stmt = node

        while isinstance(cur, ast.If):
            # inline comment is stored in ast.If.test
            cur_desc, cur_cfg = helpers.get_desc(cur.test)
            if "hide" in cur_cfg:
                return StmtLatex(None, cur_desc)

            with config.override(**cur_cfg):
                test_cond = helpers.get_object(cur.test, self.ns)

                if test_cond is None or not config.show_substitution:
                    if helpers.is_piecewise_if(node):
                        return self.visit_piecewise_if(node)
                    return self.visit_definition_if(node)

                if test_cond:
                    test = displays.definition(cur.test, self.ns)

                    if config.show_substitution:
                        test_sub = displays.substitution(cur.test, self.ns)

                        if test != test_sub and not (
                            isinstance(cur.test, ast.Compare)
                            and len(cur.test.ops) == 1
                            and isinstance(cur.test.ops[0], ast.Eq)
                        ):
                            test += r"\ \to\ " + test_sub

                    if len(cur.body) == 1 and isinstance(cur.body[0], ast.Pass):
                        cur_latex = None
                        cur_body = []
                    else:
                        cur_latex = r"\text{Since}\ " + test + r" \text{:}"
                        cur_body = self.visit_body(cur.body)

                    return StmtLatex(cur_latex, cur_desc, cur_body)

            if len(cur.orelse) > 1:
                # an "else" block
                orelse = cur.orelse

                if isinstance(orelse[0], ast_c.Comment):
                    orelse_desc, orelse_cfg = helpers.get_desc(orelse[0])
                    if "hide" in orelse_cfg:
                        return StmtLatex(None, orelse_desc)
                    orelse = orelse[1:]
                else:
                    orelse_desc, orelse_cfg = None, {}

                with config.override(**orelse_cfg):
                    orelse_body = self.visit_body(orelse)

                return StmtLatex(None, orelse_desc, orelse_body)

            if len(cur.orelse) == 1:
                # either an "elif" or a single statement for "else"
                cur = cur.orelse[0]
            else:
                return StmtLatex(None)

        orelse_body = [self.visit(cur)]

        return StmtLatex(None, body=orelse_body)

    def visit_Import(self, node: ast.Import) -> StmtLatex:
        """Visit an import."""

        desc, _ = helpers.get_desc(node)
        return StmtLatex(None, desc)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> StmtLatex:
        """Visit a from x import y statement."""

        desc, _ = helpers.get_desc(node)
        return StmtLatex(None, desc)

    def visit_Expr(self, node: ast.Expr) -> StmtLatex:
        """Visit an expression statement."""

        desc, cfg = helpers.get_desc(node)
        if "hide" in cfg:
            return StmtLatex(None, desc)

        with config.override(**cfg):
            if self.ns:
                special = convert_block(node, self.ns)
                if special is not None:
                    return special

            modes = displays.all_modes(node.value, self.ns)

            if modes:
                lhs, *rhs = modes
                latex = formatters.format_equation(lhs, rhs)
            else:
                latex = None

            return StmtLatex(latex, desc)

    def visit_Pass(self, node: ast.Pass) -> StmtLatex:
        """Visit a pass statement."""

        desc, _ = helpers.get_desc(node)
        return StmtLatex(None, desc)

    # pylint: disable-next=too-many-locals
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

        args: list[str] = []

        for posonlyarg, pos_def in zip(node.posonlyargs, pos_defs):
            args.append(self.visit_arg(posonlyarg, pos_def))
        for arg, default in zip(node.args, defaults):
            args.append(self.visit_arg(arg, default))
        if node.vararg:
            args.append("*" + self.visit_arg(node.vararg))
        for kwonlyarg, kw_default in zip(node.kwonlyargs, node.kw_defaults):
            args.append(self.visit_arg(kwonlyarg, kw_default))
        if node.kwarg:
            args.append("**" + self.visit_arg(node.kwarg))

        prefix, sep, suffix = rules.CALL_ARGS_SYNTAX

        return formatters.format_delims(prefix, sep.join(args), suffix)

    def visit_arg(
        self, node: ast.arg, default_node: ast.expr | None = None
    ) -> str:
        """Visit an argument of a function definition."""

        arg = formatters.format_name(node.arg)

        if default_node:
            default = displays.definition(default_node, self.ns)
            return f"{arg}{rules.KWARG_ASSIGN}{default}"

        return arg

    # pylint: disable-next=too-many-locals
    def visit_piecewise_funcdef(
        self, node: ast.FunctionDef, *, ns: dict[str, object]
    ) -> StmtLatex:
        """Visit an ast.FunctionDef in piecewise form.

        For example:
            def sgn(x):  # @cfg desc
                if x > 1:
                    return 1
                if x < 1:
                    return -1
                return 0
        """

        # only the inline comment on functiondef is used for rendering
        desc, cfg = helpers.get_desc(node.body[0])
        if "hide" in cfg:
            return StmtLatex(None, desc)

        body = helpers.strip_body_comments(node.body)

        with config.override(**cfg):
            name = formatters.format_name(node.name, call=True)
            args = self.visit_arguments(node.args)

            defs: list[str] = []
            subs: list[str] = []

            prefix, if_syntax, sep, else_syntax, suffix = rules.PIECEWISE_SYNTAX

            for stmt in body:
                assert isinstance(stmt, (ast.If, ast.Return))

                cur: ast.If | ast.Return = stmt

                while isinstance(cur, ast.If):
                    _, cur_cfg = helpers.get_desc(cur.test)

                    cur_body = helpers.strip_body_comments(cur.body)
                    cur_orelse = helpers.strip_body_comments(cur.orelse)

                    assert len(cur_body) == 1
                    assert isinstance(cur_body[0], ast.Return)
                    assert len(cur_orelse) < 2

                    if "hide" not in cur_cfg:
                        with config.override(**cur_cfg):
                            ret = cur_body[0]

                            _, ret_cfg = helpers.get_desc(ret)

                            assert ret.value is not None

                            with config.override(**ret_cfg):
                                value = displays.definition(ret.value, ns)
                                sub = displays.substitution(ret.value, ns)
                                test = displays.definition(cur.test, ns)

                        defs.append(if_syntax(value, test))
                        subs.append(if_syntax(sub, test))

                    if not cur_orelse:
                        break

                    assert isinstance(cur_orelse[0], (ast.If, ast.Return))

                    cur = cur_orelse[0]

                if isinstance(cur, ast.Return) and cur.value:
                    _, cur_cfg = helpers.get_desc(cur)

                    if "hide" not in cur_cfg:
                        with config.override(**cur_cfg):
                            value = displays.definition(cur.value, ns)
                            sub = displays.substitution(cur.value, ns)

                        defs.append(else_syntax(value))
                        subs.append(else_syntax(sub))

            def_latex = formatters.format_delims(prefix, sep.join(defs), suffix)
            sub_latex = formatters.format_delims(prefix, sep.join(subs), suffix)

            rhs = [def_latex]
            if config.show_substitution and sub_latex not in rhs:
                rhs.append(sub_latex)

            latex = formatters.format_equation(f"{name} {args}", rhs)

            return StmtLatex(latex, desc)

    def visit_assign_targets(self, targets: list[ast.expr]) -> list[str]:
        """Visit an assignment target(s)."""

        lhs: list[str] = []
        for target in targets:
            if isinstance(target, ast.Tuple):
                elts = [displays.definition(e, self.ns) for e in target.elts]
                lhs.append(r",\, ".join(elts))
            else:
                lhs.append(displays.definition(target, self.ns))

        return lhs

    # pylint: disable-next=too-many-locals,too-many-statements
    def visit_piecewise_if(self, node: ast.If) -> StmtLatex:
        """Visit an ast.If in piecewise form.

        For example:
            if x < a:
                y = x + a  # desc
            elif x > a:
                y = x - a
            else:
                y = x

        The rendered statement never includes a substitution form.
        """

        cur: ast.If | ast.Assign = node
        lhs: list[str] = []
        defs: list[str] = []
        res_latex: str = ""

        prefix, if_syntax, sep, else_syntax, suffix = rules.PIECEWISE_SYNTAX

        while isinstance(cur, ast.If):
            _, cur_cfg = helpers.get_desc(cur.test)
            if "hide" in cur_cfg:
                continue

            cur_body = helpers.strip_body_comments(cur.body)
            cur_orelse = helpers.strip_body_comments(cur.orelse)

            assert len(cur_body) == 1
            assert isinstance(cur_body[0], ast.Assign)
            assert len(cur_orelse) < 2

            if "hide" not in cur_cfg:
                with config.override(**cur_cfg):
                    assign = cur_body[0]

                    _, assign_cfg = helpers.get_desc(assign)

                    with config.override(**assign_cfg):
                        if not lhs:
                            lhs = self.visit_assign_targets(assign.targets)
                            if self.ns:
                                res_latex = displays.result(
                                    assign.targets[0], self.ns
                                )

                        value = displays.definition(assign.value, self.ns)
                        test = displays.definition(cur.test, self.ns)

                defs.append(if_syntax(value, test))

            if not cur_orelse:
                break

            assert isinstance(cur_orelse[0], (ast.If, ast.Assign))

            cur = cur_orelse[0]

        if isinstance(cur, ast.Assign):
            _, cur_cfg = helpers.get_desc(cur)

            if "hide" not in cur_cfg:
                with config.override(**cur_cfg):
                    value = displays.definition(cur.value, self.ns)

                defs.append(else_syntax(value))

        def_latex = formatters.format_delims(prefix, sep.join(defs), suffix)

        rhs = []
        if config.show_definition:
            rhs.append(def_latex)
        if config.show_result:
            rhs.append(res_latex)

        latex = formatters.format_equation(lhs, rhs)

        # the inline comment on the first branch is used as desc
        desc, _ = helpers.get_desc(node.body[0])

        return StmtLatex(latex, desc)

    def visit_definition_if(self, node: ast.If) -> StmtLatex:
        """Visit an ast.If and show all its conditions without any
        substitution.

        Returns a headless StmtLatex with a body of StmtLatexes for
        each conditional branch.
        """

        cur: ast.stmt = node
        stmt_latex_body: list[StmtLatex] = []

        while isinstance(cur, ast.If):
            # inline comment is stored in ast.If.test
            cur_desc, cur_cfg = helpers.get_desc(cur.test)  # sure not cur?

            if "hide" not in cur_cfg:
                with config.override(**cur_cfg):
                    test = displays.definition(cur.test, self.ns)
                    if_ = "If" if not stmt_latex_body else "Else, if"

                    cur_latex = r"\text{" + if_ + r"}\ " + test + r" \text{:}"
                    cur_body = self.visit_body(cur.body)

                stmt_latex_body.append(StmtLatex(cur_latex, cur_desc, cur_body))

            if len(cur.orelse) > 1:
                # an "else" block
                orelse = cur.orelse

                if isinstance(orelse[0], ast_c.Comment):
                    # inline comment is stored in ast.If.orelse[0]
                    orelse_desc, orelse_cfg = helpers.get_desc(orelse[0])
                    orelse = orelse[1:]
                else:
                    orelse_desc, orelse_cfg = None, {}

                if "hide" not in orelse_cfg:
                    with config.override(**orelse_cfg):
                        orelse_latex = r"\text{Otherwise:}"
                        orelse_body = self.visit_body(orelse)

                    stmt_latex_body.append(
                        StmtLatex(orelse_latex, orelse_desc, orelse_body)
                    )

            elif len(cur.orelse) == 1:
                # either an "elif" or a single statement for "else"
                cur = cur.orelse[0]

            else:
                return StmtLatex(None, body=stmt_latex_body)

        orelse_latex = r"\text{Otherwise:}"
        orelse_body = [self.visit(cur)]
        stmt_latex_body.append(StmtLatex(orelse_latex, body=orelse_body))

        return StmtLatex(None, body=stmt_latex_body)

    def visit_body(self, body: list[ast.stmt]) -> list[StmtLatex]:
        """Visit each ast.stmt in an ast.stmt body."""

        latexes: list[StmtLatex] = []
        desc_block: list[str] = []
        body_cfg: dict[str, bool | int | Iterable[str]] = {}
        hide: bool = False

        for b in body:
            if isinstance(b, ast_c.Comment):
                desc, cfg = helpers.get_desc(b)
                if "hide" in cfg:
                    hide = True
                elif "endhide" in cfg:
                    hide = False
                else:
                    if desc_block:
                        body_cfg.update(cfg)
                    else:
                        body_cfg = cfg
                    desc_block.append(desc or "")
                continue

            if hide:
                continue

            if desc_block:
                latexes.append(StmtLatex(None, "\n".join(desc_block)))
                desc_block.clear()

            with config.override(**body_cfg):
                latexes.append(self.visit(b))

        if desc_block:
            latexes.append(StmtLatex(None, "\n".join(desc_block)))

        return latexes
