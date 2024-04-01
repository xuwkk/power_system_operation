import json
import sys
import numpy as np
sys.path.append('.')
from utils import from_pypower, return_compiler, return_standard_form, load_grid
from pypower import api
from operation import PowerGrid, Operation
import cvxpy as cp
from pprint import pprint
from cvxpy.constraints.finite_set import FiniteSet

def test_ncuc_no_int(pypower_case_name, config_path, T):

    print('run ncuc without bool variables')
    my_grid = load_grid(pypower_case_name, config_path)
    ncuc = my_grid.ncuc_no_int(T = T)

    compiler, params_idx, zero_idx, int_idx, bool_idx = return_compiler(ncuc)

    # define parameter normal random
    load = my_grid.load_default.reshape(1,-1) * 2.0 * (1 + np.random.rand(T, my_grid.no_load) * 0.4)
    pg_int = my_grid.pgmax * 0.5
    solar = my_grid.solar_default.reshape(1, -1) * (1 + np.random.rand(T, my_grid.no_solar) * 0.2)
    wind = my_grid.wind_default.reshape(1, -1) * (1 + np.random.rand(T, my_grid.no_wind) * 0.2)
    reserve = np.random.rand(T) * 0.2

    params_val_dict = {
        "load": load,
        "pg_init": pg_int,
        "solar": solar,
        "wind": wind,
        "reserve": reserve
    }

    # solve on the original formulation
    my_grid.solve(ncuc, params_val_dict)

    print('optimal value by original form:', ncuc.value)

    # solve by the standard form
    params_val = {idx: params_val_dict[name] for idx, name in params_idx.items()}

    P, q, r, A, b, G, h  = return_standard_form(compiler, 
                                            params_val, 
                                            zero_dim = zero_idx)
    
    x = cp.Variable(P.shape[1])
    objective = cp.Minimize(0.5 * cp.quad_form(x, P) + q @ x + r)
    constraints = [A @ x == b, G @ x <= h]
    prob = cp.Problem(objective, constraints)
    prob.solve(solver = cp.GUROBI, verbose = False)

    print('optimal value by standard form:', prob.value)
    print('these two values should be the same.')

def test_ncuc_with_int(pypower_case_name, config_path, T):

    print('run ncuc with bool variables')
    my_grid = load_grid(pypower_case_name, config_path)

    ncuc = my_grid.ncuc_with_int(T = T)

    compiler, params_idx, zero_idx, int_idx, bool_idx = return_compiler(ncuc)

    # define parameter
    # normal random
    # ug_int = np.ones((my_grid.no_gen))
    ug_init = np.zeros((my_grid.no_gen))
    load_scale = 1.0
    load = my_grid.load_default.reshape(1,-1) * load_scale * (1 + np.random.rand(T, my_grid.no_load) * 0.4)
    pg_int = my_grid.pgmax * 0.5
    solar = my_grid.solar_default.reshape(1, -1) * (1 + np.random.rand(T, my_grid.no_solar) * 0.2)
    wind = my_grid.wind_default.reshape(1, -1) * (1 + np.random.rand(T, my_grid.no_wind) * 0.2)
    reserve = np.random.rand(T) * 0.2

    params_val_dict = {
        "load": load,
        "pg_init": pg_int,
        "solar": solar,
        "wind": wind,
        "reserve": reserve,
        "ug_init": ug_init
    }

    # solve on the original formulation
    my_grid.solve(ncuc, params_val_dict)

    print('optimal value by original form:', ncuc.value)

    # solve by the standard form
    params_val = {idx: params_val_dict[name] for idx, name in params_idx.items()}

    P, q, r, A, b, G, h  = return_standard_form(compiler, 
                                            params_val, 
                                            zero_dim = zero_idx)

    x = cp.Variable(P.shape[1])
    objective = cp.Minimize(0.5 * cp.quad_form(x, P) + q @ x + r)
    constraints = [A @ x == b, G @ x <= h]

    if len(bool_idx) > 0:
        constraints += [FiniteSet(x[bool_idx], [0, 1])
                        ]
    
    prob = cp.Problem(objective, constraints)
    prob.solve(solver = cp.GUROBI, verbose = False)

    print('optimal value by standard form:', prob.value)
    print('these two values should be the same.')







if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--pypower_case_name', type=str, default="case14")
    parser.add_argument('-c', '--config_path', type=str, default="configs/case14_default.json")
    parser.add_argument('-T', '--T', type=int, default=6)
    args = parser.parse_args()

    test_ncuc_no_int(args.pypower_case_name, config_path=args.config_path, T = args.T)
    test_ncuc_with_int(args.pypower_case_name, config_path=args.config_path, T = args.T)

