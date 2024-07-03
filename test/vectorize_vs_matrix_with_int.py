"""
test if the matrix form and vectorize form are equivalent for ncuc with integer variables
"""

import sys
import numpy as np
sys.path.append('.')
from utils import load_grid
from pprint import pprint

def generate_data(my_grid, T):

    ug_init = np.zeros((my_grid.no_gen))
    load_scale = 1.0
    load = my_grid.load_default.reshape(1,-1) * load_scale * (1 + np.random.rand(T, my_grid.no_load) * 0.4)
    pg_int = my_grid.pgmax * 0.5
    solar = my_grid.solar_default.reshape(1, -1) * (1 + np.random.rand(T, my_grid.no_solar) * 0.2)
    wind = my_grid.wind_default.reshape(1, -1) * (1 + np.random.rand(T, my_grid.no_wind) * 0.2)
    reserve = np.random.rand(T) * 0.2

    return ug_init, load, pg_int, solar, wind, reserve

def matrix_form(pypower_case_name, config_path, T, seed):

    print('======matrix formulation======')
    np.random.seed(seed)
    my_grid = load_grid(pypower_case_name, config_path, vectorize=False)
    ncuc = my_grid.ncuc_with_int(T = T)

    ug_init, load, pg_int, solar, wind, reserve = generate_data(my_grid, T)

    if T == 1:
        param_dict = {
            "load": load[0],
            "solar": solar[0],
            "wind": wind[0],
            "reserve": reserve[0],
        }
    else:
        param_dict = {
            "load": load,
            "pg_init": pg_int,
            "solar": solar,
            "wind": wind,
            "reserve": reserve,
            "ug_init": ug_init
        }

    print('total_load:', np.sum(load, 1))
    print('total_capacity:', np.sum(my_grid.pgmax) + np.sum(solar, 1) + np.sum(wind, 1))
    print('reserve:', reserve)

    my_grid.solve(ncuc, param_dict) # in place

    if ncuc.status != 'optimal':
        print('Optimization failed')
        return
    else:
        optimal_value = ncuc.value
        optimal_sol = my_grid.get_sol(ncuc)
        optimal_sol = {k: np.round(v, 3) for k, v in optimal_sol.items()}
    
    return optimal_value, optimal_sol

def vectorize_form(pypower_case_name, config_path, T, seed):

    print("======vectorize formulation======")

    np.random.seed(seed)

    my_grid = load_grid(pypower_case_name, config_path, vectorize=True)
    ncuc = my_grid.ncuc_with_int(T = T)

    ug_init, load, pg_int, solar, wind, reserve = generate_data(my_grid, T)

    if T == 1:
        param_dict = {
            "load": load[0],
            "solar": solar[0],
            "wind": wind[0],
            "reserve": reserve[0],
        }
    else:
        param_dict = {
            "load": load.flatten(),
            "pg_init": pg_int,
            "solar": solar.flatten(),
            "wind": wind.flatten(),
            "reserve": reserve,
            "ug_init": ug_init
        }
    
    print('total_load:', np.sum(load.reshape(T,-1), 1))
    print('total_capacity:', 
        np.sum(my_grid.pgmax) + np.sum(solar.reshape(T,-1), 1) + np.sum(wind.reshape(T,-1), 1))
    print('reserve:', reserve)

    my_grid.solve(ncuc, param_dict) # in place

    if ncuc.status != 'optimal':
        print('Optimization failed')
        return
    else:
        optimal_value = ncuc.value
        optimal_sol = my_grid.get_sol(ncuc)
        optimal_sol = {k: np.round(v.reshape(T,-1), 3) for k, v in optimal_sol.items()}
    
    return optimal_value, optimal_sol


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--pypower_case_name', type=str, default="case14")
    parser.add_argument('-c', '--config_path', type=str, default="configs/case14_default.json")
    parser.add_argument('-T', '--T', type=int, default=6)
    parser.add_argument('-s', '--seed', type=int, default=1)
    args = parser.parse_args()

    value_matrix, sol_matrix = matrix_form(args.pypower_case_name, config_path=args.config_path, T = args.T, seed=args.seed)
    value_vectorize, sol_vectorize = vectorize_form(args.pypower_case_name, config_path=args.config_path, T = args.T, seed=args.seed)

    assert np.isclose(value_matrix, value_vectorize), "Optimal value is different"
    for k in sol_matrix:
        assert np.allclose(sol_matrix[k], sol_vectorize[k]), f"Optimal solution for {k} is different"
    
    print('all tests passed!')