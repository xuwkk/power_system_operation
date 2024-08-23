"""
test the optimization problem for the case with integer variables
"""

import sys
import numpy as np
sys.path.append('.')
from utils import get_data, load_grid_from_xlsx, return_standard_form_in_cvxpy
from tqdm import tqdm

def test(args):
    
    np.random.seed(0)
    
    # operation paraemter
    T = 24
    with_int = True
    reserve = 0.0
    pg_init_ratio = 0.5
    ug_init = 1
    
    grid_op = load_grid_from_xlsx(
        xlsx_path = f"configs/{args.pypower_case_name}.xlsx", T = T, 
        reserve = reserve, 
        pg_init_ratio = pg_init_ratio, ug_init = ug_init
        )
    
    load_all, solar_all, wind_all = get_data(
        no_load = grid_op.no_load, 
        data_folder = f"data/{args.pypower_case_name}/", 
        grid_op = grid_op
        )
    
    # formulate the cvxpy problem
    uc_cvxpy, ed_cvxpy = grid_op.get_opt(with_int)
    
    no_var_uc_cvxpy = 0
    for var in uc_cvxpy.variables():
        no_var_uc_cvxpy += np.prod(var.shape)
    no_var_ed_cvxpy = 0
    for var in ed_cvxpy.variables():
        no_var_ed_cvxpy += np.prod(var.shape)
    
    # obtain the standard form
    uc_stand = return_standard_form_in_cvxpy(uc_cvxpy)
    ed_stand = return_standard_form_in_cvxpy(ed_cvxpy)
    no_var_uc_stand = 0
    for var in uc_stand.variables():
        no_var_uc_stand += np.prod(var.shape)
    no_var_ed_stand = 0
    for var in ed_stand.variables():
        no_var_ed_stand += np.prod(var.shape)
    
    assert no_var_uc_cvxpy == no_var_uc_stand, "the number of variables in the uc problem is not consistent"
    assert no_var_ed_cvxpy == no_var_ed_stand, "the number of variables in the ed problem is not consistent"

    # no_sample = load_all.shape[0] - T + 1
    sample_idx = np.random.choice(load_all.shape[0] - T + 1, args.no_sample, replace = False)
    # sample_idx = [1172]
    
    for i in tqdm(sample_idx):
        
        """
        cvxpy solution
        """
        
        # solve uc
        load_forecast = load_all[i:i+T] * (0.8 + np.random.rand(*load_all[i:i+T].shape) * 0.4)
        params_val_dict_uc = {
            'load': load_forecast.flatten()
        }
        if solar_all is not None:
            solar_forecast = solar_all[i:i+T] * (0.8 + np.random.rand(*solar_all[i:i+T].shape) * 0.4)
            params_val_dict_uc['solar'] = solar_forecast.flatten()
        if wind_all is not None:
            wind_forecast = wind_all[i:i+T] * (0.8 + np.random.rand(*wind_all[i:i+T].shape) * 0.4)
            params_val_dict_uc['wind'] = wind_forecast.flatten()
        grid_op.solve(uc_cvxpy, params_val_dict_uc)
        value_uc_cvxpy = uc_cvxpy.value
        uc_sol_cvxpy = grid_op.get_sol(uc_cvxpy)
        
        # solve ed
        params_val_dict_ed = {
            'load': load_all[i:i+T].flatten(),
            'pg_uc': uc_sol_cvxpy['pg'],
            'ug': uc_sol_cvxpy['ug']
        }
        if solar_all is not None:
            params_val_dict_ed['solar'] = solar_all[i:i+T].flatten()
        if wind_all is not None:
            params_val_dict_ed['wind'] = wind_all[i:i+T].flatten()
        grid_op.solve(ed_cvxpy, params_val_dict_ed)
        value_ed_cvxpy = ed_cvxpy.value
        ed_sol_cvxpy = grid_op.get_sol(ed_cvxpy)
        
        """
        standard form solution
        """
        # uc problem
        grid_op.solve(uc_stand, params_val_dict_uc)
        value_uc_stand = uc_stand.value
        uc_sol_stand = uc_stand.variables()[0].value
        uc_pg_stand = uc_sol_stand[:T*grid_op.no_gen]
        uc_ug_stand = uc_sol_stand[T*grid_op.no_gen:T*grid_op.no_gen*2]
        
        # ed problem
        params_val_dict_ed['pg_uc'] = uc_pg_stand
        params_val_dict_ed['ug'] = uc_ug_stand
        
        grid_op.solve(ed_stand, params_val_dict_ed)
        value_ed_stand = ed_stand.value
        ed_sol_stand = ed_stand.variables()[0].value
        
        # print('uc value diff:', value_uc_cvxpy - value_uc_stand)
        # print('uc ug diff:', np.sum(np.abs(uc_sol_cvxpy['ug'] - uc_ug_stand)))
        # print('uc pg diff:', np.sum(np.abs(uc_sol_cvxpy['pg'] - uc_pg_stand)))
        # print('ed value diff:', value_ed_cvxpy - value_ed_stand)
        
        # todo: further reduce the tolerance of gurobi
        assert np.abs(value_uc_cvxpy - value_uc_stand) / np.abs(value_uc_cvxpy) < 1e-2, f"uc value is not consistent for sample {i}"
        assert np.abs(value_ed_cvxpy - value_ed_stand) / np.abs(value_ed_cvxpy) < 1e-2, f"ed value is not consistent for sample {i}"
    
if __name__ == "__main__":
    
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--pypower_case_name', type=str, default="case14")
    parser.add_argument('--no_sample', type=int, default = 100)
    args = parser.parse_args()
    
    test(args)