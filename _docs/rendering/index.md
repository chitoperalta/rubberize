# Expression and Statement Rendering

This guide provides an overview of how Rubberize renders various Python expressions and statements.

## Table of Contents

### Expressions
- [Variables](variables.md)
- [Numbers](numbers.md)
- [Collections](collections.md)
- [Other Built-in Types](builtins.md)
- [Class and Function Calls](calls.md)
- [Custom Types and Calls](custom_types.md)
- [Physical Quantities (Pint)](pint.md)
- [Arrays (NumPy)](numpy.md)
- [Operators and Expressions](expressions.md)
<!-- - TODO [Symbolic Expressions (SymPy)](sympy.md) -->

### Statements
- [Assignments](assignments.md)
- [Conditional Statements](conditionals.md)
- [Function Definitions](funcdefs.md)
<!-- - TODO [Calc Sheet Component](calcsheet_component.md) -->


## Supported Python Features (as of 0.3.x)

This table summarizes the Python features supported by Rubberize. Since Rubberize uses the `ast` library to generate mathematical LaTeX code, each feature is directly linked to its corresponding `ast` node.

### Expressions

| Feature                             | `ast` Node Name  | Support            | Example Render                                                    |
| ----------------------------------- | ---------------- | ------------------ | ----------------------------------------------------------------- |
| Boolean Operations                  | `BoolOp`         | :white_check_mark: | [See here](expressions.md#boolean-operations)                     |
| Named Expressions (`:=` operation)  | `NamedExpr`      | :white_check_mark: | `a := b` $a \gets b$                                              |
| Binary Operations                   | `BinOp`          | :white_check_mark: | [See here](expressions.md#binary-operations)                      |
| Unary Opterations                   | `UnaryOp`        | :white_check_mark: | [See here](expressions.md#unary-operations)                       |
| Lambda Functions                    | `NamedExpr`      | :white_check_mark: | `lambda x: x+1` $x \mapsto x + 1$                                 |
| Conditional Expressions             | `IfExp`          | :white_check_mark: | [See here](expressions.md#conditional-expressions)                |
| Dictionary                          | `Dict`           | :white_check_mark: | [See here](collections.md#dictionaries)                           |
| Set                                 | `Set`            | :white_check_mark: | [See here](collections.md#sets)                                   |
| List Comprehension                  | `ListComp`       | :white_check_mark: | [See here](collections.md#list-comprehension)                     |
| Set Comprehension                   | `SetComp`        | :white_check_mark: | [See here](collections.md#set-comprehension)                      |
| Dictionary Comprehension            | `DictComp`       | :white_check_mark: | [See here](collections.md#dictionary-comprehension)               |
| Generator Expressions               | `GeneratorExp`   | :white_check_mark: | Similar to list comp                                              |
| Await                               | `Await`          | :x:                |                                                                   |
| Yield                               | `Yield`          | :x:                |                                                                   |
| Yield From                          | `YieldFrom`      | :x:                |                                                                   |
| Comparisons                         | `Compare`        | :white_check_mark: | [See here](expressions.md#comparisons)                            |
| Calls                               | `Call`           | :white_check_mark: | [See here](calls.md)                                              |
| Formatting Field in an f-string     | `FormattedValue` | :x:                |                                                                   |
| f-string                            | `JoinedStr`      | :x:                |                                                                   |
| Integer, float, and complex numbers | `Constant`       | :white_check_mark: | [See here](numbers.md)                                            |
| Other Built-in Types                | `Constant`       | :white_check_mark: | [See here](builtins.md)                                           |
| Attribute access                    | `Attribute`      | :white_check_mark: | [See here](variables.md#attribute-access)                         |
| Subscript access                    | `Subscript`      | :white_check_mark: | [See here](collections.md#accessing-collection-elements)          |
| Tuple unpacking                     | `Starred`        | :white_check_mark: | `*a` $*a$                                                         |
| Identifier names                    | `Name`           | :white_check_mark: | [See here](variables.md)                                          |
| Lists                               | `List`           | :white_check_mark: | [See here](collections.md#lists)                                  |
| Tuples                              | `Tuple`          | :white_check_mark: | [See here](collections.md#tuples)                                 |
| Subscript slices                    | `Slice`          | :white_check_mark: | [See here](collections.md#accessing-elements-of-lists-and-tuples) |

### Statements

| Feature                        | `ast` Node Name        | Support                 | Example Render                                               |
| ------------------------------ | ---------------------- | ----------------------- | ------------------------------------------------------------ |
| Function Definitions           | `FunctionDef`          | :white_check_mark:      | [See here](funcdefs.md)                                       |
| Async Function Definitions     | `AsyncFunctionDef`     | :x:                     |                                                              |
| Class Definitions              | `ClassDef`             | :x:                     |                                                              |
| Return Statement               | `Return`               | :large_orange_diamond: | Depends; [see here](funcdefs.md)                              |
| Delete Statement               | `Delete`               | :x:                     |                                                              |
| Assignments                    | `Assign`               | :white_check_mark:      | [See here](assignments.md)                                   |
| Type Statement                 | `TypeAlias`            | :x:                     |                                                              |
| Augmented Assignments (`+=`)   | `AugAssign`            | :x:                     |                                                              |
| Annotated Assignments          | `AnnAssign`            | :large_orange_diamond: | No effect; [see here](assignments.md#annotated-assignments) |
| For Loops                      | `For`                  | :x:                     |                                                              |
| Async For Loops                | `AsyncFor`             | :x:                     |                                                              |
| While Loops                    | `While`                | :x:                     |                                                              |
| Conditional Statements         | `If`                   | :white_check_mark:      | [See here](conditionals.md)                                  |
| With Blocks (Context managers) | `With`                 | :x:                     |                                                              |
| Async With Blocks              | `AsyncWith`            | :x:                     |                                                              |
| Match Blocks                   | `Match`                | :x:                     |                                                              |
| Raise Statements               | `Raise`                | :x:                     |                                                              |
| Try Blocks                     | `Try`, `TryStar`       | :x:                     |                                                              |
| Assert Statements              | `Assert`               | :x:                     |                                                              |
| Import Statements              | `Import`, `ImportFrom` | :large_orange_diamond: | Hidden                                                       |
| Global Statements              | `Global`               | :x:                     |                                                              |
| Nonlocal Statements            | `Nonlocal`             | :x:                     |                                                              |
| Expression Statements          | `Expr`                 | :white_check_mark:      | [See here](expressions.md)                                   |
| Pass Statements                | `Pass`                 | :large_orange_diamond: | Hidden                                                       |
| Break Statements               | `Break`                | :x:                     |                                                              |
| Continue Statements            | `Continue`             | :x:                     |                                                              |
