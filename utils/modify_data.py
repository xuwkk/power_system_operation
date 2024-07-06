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

def assign_data(xlsx_dir, no_load, no_solar, no_wind, save_dir, seed, force_new = False):
    """
    xlsx_dir: the path to the configuration file in xlsx
    no_load, no_solar, no_wind: the number of load, solar, and wind data to assign
    save_dir: the directory to save the assigned data
    seed: the random seed
    force_new: if True, the function will assign new data even if the directory exists
    """
    
    print("==========assign data to load and rescale==========")

    if not force_new:
        if not os.path.exists(save_dir):
            print(f"directory {save_dir} does not exist, please set force_new = True to generate the data")
        return 

    np.random.seed(seed)
    random.seed(seed)

    load_config = pd.read_excel(xlsx_dir, sheet_name='load', engine='openpyxl')
    data_all = {key: [] for key in range(1, no_load + 1)}

    data_grouped_dir = 'data/data_grouped'
    file_name = os.listdir(data_grouped_dir)
    assigned_name = []

    # assign solar
    if no_solar > 0:
        solar_config = pd.read_excel(xlsx_dir, sheet_name='solar', engine='openpyxl')
        for i in range(len(solar_config)):
            bus_idx = solar_config['idx'][i]
            load_idx = load_config[load_config['idx'] == bus_idx].index.values[0] + 1
            for name in file_name:
                if '.csv' in name and name not in assigned_name:
                    data = pd.read_csv(os.path.join(data_grouped_dir, name))
                    if np.sum(data['Solar']) > 0: # the data contains solar
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
    
    if no_wind > 0:
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

    # for name in remaining_file_name:
    #     data = pd.read_csv(os.path.join(data_grouped_dir, name))
    #     max_load = np.max(data['Load'])
    #     for i in range(1, no_load + 1):
    #         if len(data_all[i]) == 0: # the load has not been assigned
    #             default_load = load_config['default'][i - 1]
    #             data['Load'] = data['Load'] * default_load / max_load
    #             data['Solar'] = 0     # pure load bus
    #             data['Wind'] = 0
    #             data_all[i] = data
    #             assigned_name.append(name)
    #             break
    
    # save the data  
    if os.path.exists(save_dir):
        shutil.rmtree(save_dir)
    
    os.makedirs(save_dir)
    
    for i in range(1, no_load + 1):
        data_all[i].to_csv(os.path.join(save_dir, f'data_{i}.csv'), index=False)

def modify_pfmax(grid_op, opt_name, T, data_folder, min_pfmax, xlsx_dir):
    """
    reduce the maximum branch limits (so that the grid optimization is not trivial)
    grid_op: the grid operation class
    opt_name: the name of the optimization problem
    T: the number of time steps
    data_folder: the folder that contains the data
    min_pfmax: the minimum branch flow limits
    """

    print("==========modify the maximum branch limits==========")

    # monitor the maximum branch limits of each transmission line
    no_load = grid_op.no_load

    print('no grid:', no_load)

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
    solar_all = np.array(solar_all).T / grid_op.baseMVA
    wind_all = np.array(wind_all).T / grid_op.baseMVA

    no_sample = load_all.shape[0]
    # no_sample = 200

    print('load, solar, wind shape')
    print(load_all.shape, solar_all.shape, wind_all.shape)

    # start at the maximum generator output
    grid_op.pfmax = np.ones(grid_op.no_branch) * np.max(grid_op.pgmax)
    prob = getattr(grid_op, opt_name)(T = T)

    best_pfmax = np.copy(grid_op.pfmax)
    
    pf_summary = []
    infeasible_indicator = 0
    
    for i in trange(no_sample - T + 1, desc='solve the grid'):
        params_val_dict = {
            "load": load_all[i:i + T],
            "solar": solar_all[i:i + T],
            "wind": wind_all[i:i + T],
            "reserve": np.zeros(T),
            "pg_init": grid_op.pgmax * 0.5
        }

        grid_op.solve(prob, params_val_dict)

        for variable in prob.variables():
            if variable.name() == 'theta':
                theta = variable.value
            if variable.name() == 'ls':
                ls_indicator = np.sum(variable.value)
            if variable.name() == 'solarc':
                solarc_indicator = np.sum(variable.value)
            if variable.name() == 'windc':
                windc_indicator = np.sum(variable.value)
        
        if ls_indicator > 0 or solarc_indicator > 0 or windc_indicator > 0:
            infeasible_indicator += 1
        
        pf = grid_op.get_pf(theta)
        pf_summary.append(pf)

    pf_summary = np.concatenate(pf_summary, axis=0)
    pf_max = np.max(np.abs(pf_summary), axis=0)
    
    print('max pf:', pf_max)

    # modify the maximum branch limits
    config = pd.read_excel(xlsx_dir, sheet_name=None, engine='openpyxl')
    config['branch']['pfmax'] = np.clip(pf_max, a_min=min_pfmax, a_max=None) * grid_op.baseMVA

    # save
    with pd.ExcelWriter(xlsx_dir, engine='xlsxwriter') as writer:
        for element_name, element_df in config.items():
            element_df.to_excel(writer, sheet_name=element_name, index=False)