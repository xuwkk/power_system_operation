"""
test the standard form conversion for vectorization form
"""

import json
import sys
import numpy as np
sys.path.append('.')
from utils import from_pypower, return_compiler, return_standard_form, load_grid, return_standard_form_no_value
from pypower import api
from operation import PowerGrid, Operation
import cvxpy as cp
from pprint import pprint
from cvxpy.constraints.finite_set import FiniteSet

def generate_data(my_grid, T, load_scale):

    ug_init = np.zeros((my_grid.no_gen))
    load = my_grid.load_default.reshape(1,-1) * load_scale * (1 + np.random.rand(T, my_grid.no_load) * 0.4)
    pg_int = my_grid.pgmax * 0.5
    solar = my_grid.solar_default.reshape(1, -1) * (1 + np.random.rand(T, my_grid.no_solar) * 0.2)
    wind = my_grid.wind_default.reshape(1, -1) * (1 + np.random.rand(T, my_grid.no_wind) * 0.2)
    reserve = np.random.rand(T) * 0.2

    return ug_init, load, pg_int, solar, wind, reserve

def ncuc_no_int(pypower_case_name, config_path, T, seed):

    print('run ncuc without bool variables')

    np.random.seed(seed)

    """
    solve by original formulation
    """

    my_grid = load_grid(pypower_case_name, config_path, vectorize=True)
    ncuc = my_grid.ncuc_no_int(T = T)

    param_qp_prog, params_idx, zero_idx, int_idx, bool_idx = return_compiler(ncuc)

    print('compiler:', param_qp_prog)
    print('params_idx:', params_idx)
    print('zero_idx:', zero_idx, '\nint no:', int_idx, '\nbool no:', bool_idx)

    ug_init, load, pg_int, solar, wind, reserve = generate_data(my_grid, T, load_scale=2.0)

    if T == 1:
        params_val_dict = {
            "load": load[0],
            "solar": solar[0],
            "wind": wind[0],
            "reserve": reserve[0]
        }
    else:
        params_val_dict = {
            "load": load.flatten(),
            "pg_init": pg_int,
            "solar": solar.flatten(),
            "wind": wind.flatten(),
            "reserve": reserve
        }
    
    """
    original formulation
    """

    # solve on the original formulation
    my_grid.solve(ncuc, params_val_dict)

    print('optimal value by original form:', ncuc.value)

    """
    solve by the standard form
    """

    params_val = {idx: params_val_dict[name] for idx, name in params_idx.items()}

    P, q, r, A, b, G, h  = return_standard_form(param_qp_prog, 
                                            params_val, 
                                            zero_dim = zero_idx)
    
    x = cp.Variable(P.shape[1])
    objective = cp.Minimize(0.5 * cp.quad_form(x, P) + q @ x + r)
    constraints = [A @ x == b, G @ x <= h]
    prob = cp.Problem(objective, constraints)
    prob.solve(solver = cp.GUROBI, verbose = False)

    print('optimal value by standard form:', prob.value)

    """
    solve by the standard form without value
    """
    P_, q_, A_, G_, b_, h_, B_, H_ = return_standard_form_no_value(param_qp_prog, zero_idx)

    # construct the b and h
    for name, val in params_val.items():
        print(name, B_[name].shape, H_[name].shape, val.shape)
        if val.ndim == 0:
            b_ = b_ + B_[name].flatten() * val
            h_ = h_ + H_[name].flatten() * val
        else:
            b_ = b_ + B_[name] @ val
            h_ = h_ + H_[name] @ val

    x = cp.Variable(P_.shape[1])
    objective = cp.Minimize(0.5 * cp.quad_form(x, P_) + q_ @ x)
    constraints = [A_ @ x == b_, G_ @ x <= h_]
    prob = cp.Problem(objective, constraints)
    prob.solve(solver = cp.GUROBI, verbose = False)

    print('optimal value by standard form without value:', prob.value)
    
    print('differences:')
    print('P:', np.linalg.norm(P - P_), P.shape, P_.shape)
    print('q:', np.linalg.norm(q - q_), q.shape, q_.shape)
    print('A:', np.linalg.norm(A - A_), A.shape, A_.shape)
    print('G:', np.linalg.norm(G - G_), G.shape, G_.shape)
    print('b:', np.linalg.norm(b - b_), b.shape, b_.shape)
    print('h:', np.linalg.norm(h - h_), h.shape, h_.shape)
    print("=====================================")


def ncuc_with_int(pypower_case_name, config_path, T, seed):

    print('run ncuc with bool variables')

    np.random.seed(seed)

    my_grid = load_grid(pypower_case_name, config_path, vectorize = True)

    ncuc = my_grid.ncuc_with_int(T = T)

    param_qp_prog, params_idx, zero_idx, int_idx, bool_idx = return_compiler(ncuc)

    print('compiler:', param_qp_prog)
    print('params_idx:', params_idx)
    print('zero_idx:', zero_idx, '\nint no:', int_idx, '\nbool no:', bool_idx)

    ug_init, load, pg_int, solar, wind, reserve = generate_data(my_grid, T, load_scale=2.0)

    if T == 1:
        params_val_dict = {
            "load": load[0],
            "solar": solar[0],
            "wind": wind[0],
            "reserve": reserve[0],
        }
    else:
        params_val_dict = {
            "load": load.flatten(),
            "pg_init": pg_int,
            "solar": solar.flatten(),
            "wind": wind.flatten(),
            "reserve": reserve,
            "ug_init": ug_init
        }

    """
    original formulation
    """

    # solve on the original formulation
    my_grid.solve(ncuc, params_val_dict)

    print('optimal value by original form:', ncuc.value)

    """
    standard form
    """
    params_val = {idx: params_val_dict[name] for idx, name in params_idx.items()}

    P, q, r, A, b, G, h  = return_standard_form(param_qp_prog, 
                                            params_val, 
                                            zero_dim = zero_idx)

    x = cp.Variable(P.shape[1])
    objective = cp.Minimize(0.5 * cp.quad_form(x, P) + q @ x + r)
    constraints = [A @ x == b, G @ x <= h]

    if len(bool_idx) > 0:
        # set the integer (binary) constraints
        constraints += [FiniteSet(x[bool_idx], [0, 1])]
    
    prob = cp.Problem(objective, constraints)
    prob.solve(solver = cp.GUROBI, verbose = False)

    print('optimal value by standard form:', prob.value)
    
    """
    solve by the standard form without value
    """
    P_, q_, A_, G_, b_, h_, B_, H_ = return_standard_form_no_value(param_qp_prog, zero_idx)

    # construct the b and h
    for name, val in params_val.items():
        if val.ndim == 0:
            b_ = b_ + B_[name].flatten() * val
            h_ = h_ + H_[name].flatten() * val
        else:
            b_ = b_ + B_[name] @ val
            h_ = h_ + H_[name] @ val

    x = cp.Variable(P_.shape[1])
    objective = cp.Minimize(0.5 * cp.quad_form(x, P_) + q_ @ x)
    constraints = [A_ @ x == b_, G_ @ x <= h_]
    if len(bool_idx) > 0:
        # set the integer (binary) constraints
        constraints += [FiniteSet(x[bool_idx], [0, 1])]
    
    prob = cp.Problem(objective, constraints)
    prob.solve(solver = cp.GUROBI, verbose = False)

    print('optimal value by standard form without value:', prob.value)
    
    print('differences:')
    print('P:', np.linalg.norm(P - P_), P.shape, P_.shape)
    print('q:', np.linalg.norm(q - q_), q.shape, q_.shape)
    print('A:', np.linalg.norm(A - A_), A.shape, A_.shape)
    print('G:', np.linalg.norm(G - G_), G.shape, G_.shape)
    print('b:', np.linalg.norm(b - b_), b.shape, b_.shape)
    print('h:', np.linalg.norm(h - h_), h.shape, h_.shape)
    print("=====================================")


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--pypower_case_name', type=str, default="case14")
    parser.add_argument('-c', '--config_path', type=str, default="configs/case14_default.json")
    parser.add_argument('-T', '--T', type=int, default=2)
    parser.add_argument('-s', '--seed', type=int, default=0)
    args = parser.parse_args()

    ncuc_no_int(args.pypower_case_name, config_path=args.config_path, T = args.T, seed=args.seed)
    ncuc_with_int(args.pypower_case_name, config_path=args.config_path, T = args.T, seed=args.seed)