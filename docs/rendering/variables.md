# Variables
Python variables are rendered considering the following rules:

- **Single letters** are rendered in italics
- **Multiple-letter chain** (i.e., words) appear roman.

```python
%%tap --dead --grid
a; b; x; y;
apple; boy; xylophone; yoyo
```

<picture>
    <source media="(prefers-color-scheme: dark)" srcset="../assets/rendering/variables/variables_dark.png">
    <source media="(prefers-color-scheme: light)" srcset="../assets/rendering/variables/variables.png">
    <img alt="Screenshot of code cell with %%tap being used" src="../assets/rendering/variables/variables.png">
</picture>

## Underscores and Subscripts

When `@use_subscripts=True`, the following rules apply:

- **Underscores** are treated as subscripts.
- **Variables with multiple words separated by underscores** (e.g., `scoo_bee_doo`) are rendered with underscores treated as subscripts. Subscripts are not nested; instead, they are displayed as a comma-separated sequence.
- **Two or more consecutive underscores escape the first underscore**. It will be shown as a literal underscore rather than indicating a subscript.
- **Leading and trailing underscores**, commonly used in Python to denote private variables, are not converted to subscripts. If the variable name includes subscripts, the leading and trailing underscores are attached to the base name (not the subscripts).

```python
%%tap --dead --grid
f_o; I_x_male; foo_bulous; foo_a_bravo_c_d
f__o; I__x_male; I_x__male; foo__a_bravo_c__d
_private; __very__private; __double__underscore__; __base_subscript__
```

<picture>
    <source media="(prefers-color-scheme: dark)" srcset="../assets/rendering/variables/subscripts_dark.png">
    <source media="(prefers-color-scheme: light)" srcset="../assets/rendering/variables/subscripts.png">
    <img alt="Screenshot of subscript treatment of Rubberize" src="../assets/rendering/variables/subscripts.png">
</picture>

## Greek Letters

When `@use_symbols=True`, the following rules apply for Python variables:

- **Greek and Hebrew letters** are rendered when their corresponding names are used. They can be used as bases or subscripts of a variable name.
- **Capital Greek letters that appear to have the same form as Latin letters are excluded**. This is to avoid cases where different variables appear similar when rendered (e.g., $\Alpha$ and $A$ might be indistinguishable).

```python
%%tap --dead -g
x_gamma; Omega_b_o; delta_max
```

<picture>
    <source media="(prefers-color-scheme: dark)" srcset="../assets/rendering/variables/greek_letters_dark.png">
    <source media="(prefers-color-scheme: light)" srcset="../assets/rendering/variables/greek_letters.png">
    <img alt="Screenshot of greek letters in Rubberize" src="../assets/rendering/variables/greek_letters.png">
</picture>

These are all the Greek and Hebrew Letter names that are converted when used. Paste them in a code cell to see each one:

```python
%%tap --dead -g
alpha; beta; Gamma, gamma; Delta, delta
epsilon, varepsilon; zeta,; eta,; Theta, theta, vartheta
iota; kappa, varkappa; Lambda, lambda_; mu
nu; Xi, xi; omicron; Pi, pi, varpi
rho, varrho; Sigma, sigma, varsigma; tau; Upsilon, upsilon
Phi, phi, varphi; chi; Psi, psi; Omega, omega
digamma; aleph; beth; gimel
```

## Diacritics, Accents, and Modifiers

When `@use_symbols=True`, the following rules also apply for Python variables:

- **Diacritics, accents and modifiers** are rendered when their corresponding names are used as after an underscore (`_`) and the name to be accented or modified.

```python
%%tap --dead -g
x_bar; k_hat; f_prime; L_star_a
```

<picture>
    <source media="(prefers-color-scheme: dark)" srcset="../assets/rendering/variables/accents_and_modifiers_dark.png">
    <source media="(prefers-color-scheme: light)" srcset="../assets/rendering/variables/accents_and_modifiers.png">
    <img alt="Screenshot of accents and modifiers in Rubberize" src="../assets/rendering/variables/accents_and_modifiers.png">
</picture>

These are all the accents and modifiers that can be converted. Paste them in a code cell to see each one:

```python
%%tap --dead -g
foo_hat; foo_widehat; foo_bar; foo_widebar; foo_tilde; foo_widetilde;
foo_dot; foo_ddot; foo_dddot; foo_ddddot; foo_breve; foo_check;
foo_acute; foo_grave; foo_ring; foo_mat; foo_vec; foo_vec2; foo_widevec2;
foo_prime; foo_star;
```

> [!Warning]
> `..._mat` and `..._vec` render similarly. They are not recommended to be used together in a single notebook, for clarity.

## What's Next?

Go back to [Expression and Statement Rendering](index.md) index to look at how other elements are rendered.