# Power System Operation in Python

**We are still at the early stage of the implementation. There will be more functionalities and flexible I/Os coming in the future. Please watch us progress to have the latest update.**

This repo contains some basic power system operations written in Python and formulated by `cvxpy`, such as:
- Network Constrained Unit Commitment (with/out integer variables)
- Economic Dispatch (ongoing)
- Stochastic Unit Commitment (ongoing)

## Key Packages

[cvxpy](https://www.cvxpy.org/): CVXPY is an open source Python-embedded modeling language for convex optimization problems. It lets you express your problem in a natural way that follows the math, rather than in the restrictive standard form required by solvers.

[pypower](https://github.com/rwl/PYPOWER): PYPOWER is a power flow and Optimal Power Flow (OPF) solver. It is a port of MATPOWER to the Python programming language.

However, you may also need to have Gurobi, Mosek or other optimization software to efficiently solve the optimization problems, especially if integers are included. Please refer [here](https://www.cvxpy.org/tutorial/advanced/index.html) for details.

## Source

The implementation of this repo follows the online cource [here](https://u.osu.edu/conejo.1/courses/power-system-operations/) and the textbook *Power System Operations*, both by Antonio Conejo [here](https://link.springer.com/book/10.1007/978-3-319-69407-8).

## Usage

### Import system from PYPOWER

The package requires a `.csv` file to contain the configuration of power system operation. The basic format follows the `MatPower` and `PyPower` styles. An example file can be found [here](configs/case14.xlsx).

We recommend to construct the `.csv` file from the basic `PyPower` file to avoid errors. To do so, you also need to provide another `.json` file to specify configs that are not covered by the `PyPower`. Please have a look [here](configs/case14_default.json). The detailed description on how to construct the extra config file can be found [here](readme_configs.md).