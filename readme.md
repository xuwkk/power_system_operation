# Power System Operation in Python

## Introduction

**We are still at the early stage of the implementation. There will be more functionalities and flexible I/Os coming in the future. Please watch us progress to have the latest update.**

The main purpose of this repository is to provide an efficient I/O for generating the optimization problem in power system operation and host a basic set of basic power system operation formulations for the future research and teaching purpose.

This repo contains some basic power system operations written in Python and formulated by `cvxpy`, such as:
- Network Constrained Unit Commitment (with/out integer variables) (finished) 
- Economic Dispatch (finished)
- Stochastic Unit Commitment (ongoing)

## Package Dependencies

[cvxpy](https://www.cvxpy.org/): is an open source Python-embedded modeling language for convex optimization problems. It lets you express your problem in a natural way that follows the math, rather than in the restrictive standard form required by solvers.

[PyPower](https://github.com/rwl/PYPOWER): is a power flow and Optimal Power Flow (OPF) solver. It is a port of MATPOWER to the Python programming language.

However, you may also need to have Gurobi, Mosek or other optimization software to efficiently solve the optimization problems, especially if integers are included. Please refer [here](https://www.cvxpy.org/tutorial/advanced/index.html) for details.

Other packages inlcudes 
```
openpyxl, XlsxWriter
```

## References

The implementation of this repo follows the online cource [here](https://u.osu.edu/conejo.1/courses/power-system-operations/) and the textbook *Power System Operations* [here](https://link.springer.com/book/10.1007/978-3-319-69407-8), both by Prof. Antonio Conejo. We also write a series of blog posts to explain the formulation used in the code, including:
- [Power system modeling](https://xuwkk.github.io/blog/posts/learning/power_system/power_system_operation.html)
- [Unit Commitment](https://xuwkk.github.io/blog/posts/learning/power_system/ncuc.html)
- [Economic Dispatch](https://xuwkk.github.io/blog/posts/learning/power_system/ed.html)

## Usage

The optimization formulation replies on reading system configuration from a `.xlsx` file. There are several ways to construct the configuration file, either from scratch or build it from existing configurations via the `PyPower` package. An example file can be found [here](configs/case14.xlsx).

### Import system from PYPOWER

We recommend to construct the `.xlsx` file from the basic `PyPower` file to avoid errors. The `PyPower` contains several grid topology and parameters that can be directly read by the package. However, you must include several necessary extra configs (that are not covered by the `PyPower`) to support the full functionality of power system operation. An example can be found [here](configs/case14_default.json). The detailed description on how to construct the extra config file can be found [here](readme_configs.md).

<!-- ### Reformulate the problem as standardard form QP/MIQP

The functions in `test/standard_form.py` are developed to reformulate the UC/ED in `cvxpy` form into the correspinding standard form. This conversion is general in addition to the UC/ED. Therefore it can be used outside power system operation. In this sense, you can "standardize" your problem by leveraging the descriptive power of `cvxpy`.

For a genenal QP without integer variable, it transforms into:
$$
\begin{array}{rl}
\min & (1/2) x^TPx + q^Tx \\
\text{s.t.} & Ax = b \\
& Gx \leq d
\end{array}
$$

For a general MIQP, it transforms into:


### Utility Test

In the `test/` folder, there are several utility test to verify the performance of the functions, including:
`test/grid_formilation.py`: to test the DC power flow matrices. -->
