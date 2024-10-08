"""
assign the grouped data to the load data of a specific grid
also rescale the load, solar, and wind data to the default scale
"""

import pandas as pd
import numpy as np
import os
import random
import shutil
import sys
sys.path.append('.')
from utils import from_pypower, return_compiler, return_standard_form
from tqdm import trange
from pprint import pprint

def assign_data(xlsx_dir, save_dir, seed, force_new = False):
    """
    xlsx_dir: the path to the configuration file in xlsx format (generated from utils.loading.py)
    save_dir: the directory to save the assigned data
    seed: the random seed
    force_new: if True, the function will assign new data even if the directory exists
    """
    
    print("========== Assign bus data to load and rescale ==========")

    if not force_new:
        if not os.path.exists(save_dir):
            print(f"directory {save_dir} does not exist, please set force_new = True to generate the data")
        else:
            print(f"directory {save_dir} exists, please set force_new = True if you want to generate new data")
        return 

    np.random.seed(seed)
    random.seed(seed)

    all_sheets = pd.read_excel(xlsx_dir, sheet_name=None, engine='openpyxl') # as a dictionary
    
    load_config = all_sheets['load']
    no_load = len(load_config)
    data_all = {key: [] for key in range(1, no_load + 1)}

    data_grouped_dir = 'data/data_grouped'
    file_name = os.listdir(data_grouped_dir)
    assigned_name = []

    # assign solar
    if 'solar' in all_sheets.keys():
        solar_config = all_sheets['solar']
        for i in range(len(solar_config)):
            # find the corresponding load index of the solar bus
            # it is assumed that the solar bus can only locate at the load bus
            bus_idx = solar_config['idx'][i]
            load_idx = load_config[load_config['idx'] == bus_idx].index.values[0] + 1
            for name in file_name:
                # go through the bus data files until the bus data contains solar has been found
                if '.csv' in name and name not in assigned_name:
                    data = pd.read_csv(os.path.join(data_grouped_dir, name))
                    if np.sum(data['Solar']) > 0: # the bus data contains solar
                        # the bus data does not have solar if the sum of solar is 0
                        assigned_name.append(name)
                        # rescale load
                        max_load = np.max(data['Load'])
                        default_load = load_config['default'][load_idx - 1]
                        data['Load'] = data['Load'] * default_load / max_load
                        # rescale solar
                        max_solar = np.max(data['Solar'])
                        default_solar = solar_config['default'][i]
                        data['Solar'] = data['Solar'] * default_solar / max_solar
                        data_all[load_idx] = data
                        break
    
    if 'wind' in all_sheets.keys():
        wind_config = pd.read_excel(xlsx_dir, sheet_name='wind', engine='openpyxl')
        for i in range(len(wind_config)):
            bus_idx = wind_config['idx'][i]
            load_idx = load_config[load_config['idx'] == bus_idx].index.values[0] + 1 # the corresponding load index of the wind bus
            for name in file_name:
                if '.csv' in name and name not in assigned_name:
                    data = pd.read_csv(os.path.join(data_grouped_dir, name))
                    if np.sum(data['Wind']) > 0: # the data contains wind
                        assigned_name.append(name)
                        # rescale load
                        max_load = np.max(data['Load'])
                        default_load = load_config['default'][load_idx - 1]
                        data['Load'] = data['Load'] * default_load / max_load
                        # recale wind
                        max_wind = np.max(data['Wind'])
                        default_wind = wind_config['default'][i]
                        data['Wind'] = data['Wind'] * default_wind / max_wind
                        data_all[load_idx] = data
                        break
    
    # for the remaining load
    # randomly choose
    remaining_file_name = [name for name in file_name if name not in assigned_name and '.csv' in name]
    remaining_file_name = np.random.choice(remaining_file_name, no_load - len(assigned_name), replace=False)

    idx = 0
    for i in range(1, no_load + 1):
        if len(data_all[i]) == 0: # the load has not been assigned
            name = remaining_file_name[idx]
            data = pd.read_csv(os.path.join(data_grouped_dir, name))
            # rescale load
            max_load = np.max(data['Load'])
            default_load = load_config['default'][i - 1]
            data['Load'] = data['Load'] * default_load / max_load
            data['Solar'] = 0     # pure load bus
            data['Wind'] = 0
            data_all[i] = data
            assigned_name.append(name)
            idx += 1
    
    # save the data  
    if os.path.exists(save_dir):
        shutil.rmtree(save_dir)
    
    os.makedirs(save_dir)
    
    for i in range(1, no_load + 1):
        data_all[i].to_csv(os.path.join(save_dir, f'data_{i}.csv'), index=False)

def get_data(no_load, data_folder, grid_op):
    """return trh scaled version data"""
    load_all, solar_all, wind_all = [], [], []

    for i in range(1, no_load + 1):
        # ! the index of the file name starts from 1 and the sequence is the same to the config file
        data = pd.read_csv(os.path.join(data_folder, f'data_{i}.csv'))
        load_all.append(data['Load'].values)
        if np.sum(data['Solar']) > 0:
            solar_all.append(data['Solar'].values)
        if np.sum(data['Wind']) > 0:
            wind_all.append(data['Wind'].values)

    load_all = np.array(load_all).T / grid_op.baseMVA
    if len(solar_all) == 0:
        solar_all = None
    else:
        solar_all = np.array(solar_all).T / grid_op.baseMVA
    if len(wind_all) == 0:
        wind_all = None
    else:
        wind_all = np.array(wind_all).T / grid_op.baseMVA

    return load_all, solar_all, wind_all

def modify_pfmax(grid_op, with_int, T, data_folder, min_pfmax, scale_factor, xlsx_dir,
                force_new = False):
    """
    reduce the maximum branch limits (so that the grid optimization is not trivially solved)
    grid_op: the grid operation class
    data_folder: the folder that contains the data
    min_pfmax: the minimum branch flow limits
    """

    print("==========modify the maximum branch limits==========")
    
    if not force_new:
        print(f"force_new is set to False, please set it to True to modify the maximum branch limits in place")
        return

    no_load = grid_op.no_load
    # start at the maximum generator output
    grid_op.pfmax = np.ones(grid_op.no_branch) * np.max(grid_op.pgmax) * 2
    print('initial pf max:', grid_op.pfmax)
    
    prob, _ = grid_op.get_opt(with_int)
    
    load_all, solar_all, wind_all = get_data(no_load, data_folder, grid_op)
    no_sample = load_all.shape[0]
    # no_sample = 2000
    pf_summary = []
    infeasible_indicator = 0
    
    load_level_summary = []
    
    for i in trange(no_sample - T + 1, desc='solve the grid'):
        
        # ! vectorized formulation of the parameter
        params_val_dict = {
            "load": load_all[i:i + T].flatten(),  
        }
        total_load = np.sum(load_all[i:i + T], axis=1)
        
        total_gen = np.sum(grid_op.pgmax)
        if solar_all is not None:
            params_val_dict['solar'] = solar_all[i:i + T].flatten()
            total_gen += np.sum(solar_all[i:i + T], axis=1)
        if wind_all is not None:
            params_val_dict['wind'] = wind_all[i:i + T].flatten()
            total_gen += np.sum(wind_all[i:i + T], axis=1)
        
        assert np.all(total_load <= total_gen), "the total load is larger than the total generation, please consider reduce the max_default_ratio of the load"
        
        load_level = np.max(total_load / total_gen)
        load_level_summary.append(load_level)
        
        grid_op.solve(prob, params_val_dict)
        
        optimal_sol = grid_op.get_sol(prob, T = T, reshaped = True)
        
        ls, solarc, windc = optimal_sol['ls'], optimal_sol['solarc'], optimal_sol['windc']
        theta = optimal_sol['theta']

        ls_indicator, solarc_indicator, windc_indicator = np.sum(ls), np.sum(solarc), np.sum(windc)
        indicator = ls_indicator + solarc_indicator + windc_indicator
        if not np.isclose(indicator, 0, atol = 1e-6):
            infeasible_indicator += 1
            # pprint(optimal_sol)
            print(f"ls: {ls_indicator}, solar: {solarc_indicator}, wind: {windc_indicator}")
            print(f"ls: {ls}")
            print(f"total load: {np.sum(load_all[i:i + T], axis=1)}")
            print(f"maximum generator: {np.sum(grid_op.pgmax)}")
            assert False, "infeasible solution meets, please try to increase the penalization of the cls."

        pf = grid_op.get_pf(theta) # a summary of the power flow
        pf_summary.append(pf)

    print("infeasible rate:", infeasible_indicator / (no_sample - T + 1))

    pf_summary = np.concatenate(pf_summary, axis=0)
    pf_max = np.max(np.abs(pf_summary), axis=0)
    print('max pf:', pf_max)
    print('max load penetration:', np.max(load_level_summary))

    # modify the maximum branch limits from the xlsx file
    config = pd.read_excel(xlsx_dir, sheet_name=None, engine='openpyxl')
    config['branch']['pfmax'] = np.clip(pf_max * scale_factor, a_min=min_pfmax, a_max=None) * grid_op.baseMVA

    # save
    with pd.ExcelWriter(xlsx_dir, engine='xlsxwriter') as writer:
        for element_name, element_df in config.items():
            element_df.to_excel(writer, sheet_name=element_name, index=False)