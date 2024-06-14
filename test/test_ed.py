"""
test economic dispatch
"""

import sys
import numpy as np
sys.path.append('.')
from utils import load_grid

def test_ed(pypower_case_name, config_path, T):

    my_grid = load_grid(pypower_case_name, config_path)
    ncuc = my_grid.ncuc_with_int(T = T)
    ed = my_grid.ed()

    """ncuc"""
    ug_init = np.zeros((my_grid.no_gen))

    load_scale = 1.5
    load = my_grid.load_default.reshape(1,-1) * load_scale * (1 + np.random.rand(T, my_grid.no_load) * 0.4)
    pg_int = my_grid.pgmax * 0.5
    solar = my_grid.solar_default.reshape(1, -1) * (1 + np.random.rand(T, my_grid.no_solar) * 0.2)
    wind = my_grid.wind_default.reshape(1, -1) * (1 + np.random.rand(T, my_grid.no_wind) * 0.2)
    # reserve = np.random.rand(T) * 0.2
    reserve = np.zeros(T)

    uc_param_dict = {
        "load": load,
        "pg_init": pg_int,
        "solar": solar,
        "wind": wind,
        "reserve": reserve,
        "ug_init": ug_init
    }

    my_grid.solve(ncuc, uc_param_dict) # in place
    optimal_sol = my_grid.get_sol(ncuc)
    pg = optimal_sol['pg']
    ug = optimal_sol['ug']

    print('UC results:')
    print(pg)
    print(ug)

    """ed"""
    # varying a little on the load, solar and wind
    idx = 1  # ! the ed is single time step
    varying_factor = 0.4
    load_true = load[idx] * (1 + np.random.rand(my_grid.no_load) * varying_factor)
    solar_true = solar[idx] * (1 + np.random.rand(my_grid.no_solar) * varying_factor)
    wind_true = wind[idx] * (1 + np.random.rand(my_grid.no_wind) * varying_factor)
    ug = ug[idx]
    pg = pg[idx]

    ed_param_dict = {
        "load": load_true,
        "solar": solar_true,
        "wind": wind_true,
        "pg": pg,
        "ug": ug
    }

    my_grid.solve(ed, ed_param_dict) # in place
    optimal_sol_ed = my_grid.get_sol(ed)
    delta_pg = optimal_sol_ed['delta_pg']
    ls = optimal_sol_ed['ls']
    windc = optimal_sol_ed['windc']
    solarc = optimal_sol_ed['solarc']

    print('ED results:')
    print('delta_pg:', delta_pg)
    print('ls:', ls)
    print('windc:', windc)
    print('solarc:', solarc)


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--pypower_case_name', type=str, default="case14")
    parser.add_argument('-c', '--config_path', type=str, default="configs/case14_default.json")
    parser.add_argument('-T', '--T', type=int, default=6)
    args = parser.parse_args()
    test_ed(args.pypower_case_name, args.config_path, args.T)