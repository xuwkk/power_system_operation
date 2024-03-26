import json
import sys
import numpy as np
sys.path.append('.')
from utils import from_pypower
from pypower import api
from operation import PowerGrid, Operation
import cvxpy as cp
from pprint import pprint

def test_ncuc(pypower_case_name, config_path, T):

    with open(config_path, "r") as f:
        my_configs = json.load(f)
    from_pypower(pypower_case_name, my_configs)
    my_grid = Operation(f"configs/{pypower_case_name}.xlsx")

    ncuc = my_grid.ncuc_no_int(T = T)

    # define parameter
    # normal random
    load = my_grid.load_default.reshape(1,-1) * 2.0 * (1 + np.random.rand(T, my_grid.no_load) * 0.4)
    pg_int = my_grid.pgmax * 0.5
    solar = my_grid.solar_default.reshape(1, -1) * (1 + np.random.rand(T, my_grid.no_solar) * 0.2)
    wind = my_grid.wind_default.reshape(1, -1) * (1 + np.random.rand(T, my_grid.no_wind) * 0.2)
    reserve = np.random.rand(T) * 0.2

    param_dict = {
        "load": load,
        "pg_init": pg_int,
        "solar": solar,
        "wind": wind,
        "reserve": reserve
    }

    print('total_load:', np.sum(load, 1))
    print('total_capacity:', np.sum(my_grid.pgmax).reshape(1, -1) + np.sum(solar, 1) + np.sum(wind, 1))
    print('reserve:', reserve)

    prob = my_grid.solve(ncuc, param_dict)

    if prob.status != 'optimal':
        print('Optimization failed')
        return
    else:
        optimal_value = prob.solve()
        optimal_sol = my_grid.get_sol(ncuc)

        print('Optimal value:', optimal_value)
        print('Optimal solution:')
        optimal_sol = {k: np.round(v, 3) for k, v in optimal_sol.items()}
        pprint(optimal_sol)
    
    pf = my_grid.get_pf(optimal_sol['theta'])
    print('Power flow:')
    print(np.round(pf, 3))

if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--pypower_case_name', type=str, default="case14")
    parser.add_argument('-c', '--config_path', type=str, default="configs/case14_default.json")
    parser.add_argument('-T', '--T', type=int, default=6)
    args = parser.parse_args()

    test_ncuc(args.pypower_case_name, config_path=args.config_path, T = args.T)
