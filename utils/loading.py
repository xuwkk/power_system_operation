"""construct the xlsx configuration file for given pypower case and extra configurations"""
from pypower import api
import numpy as np
import pandas as pd
from .pypower_idx import *
from collections.abc import Iterable
from operation import Operation
import json
from copy import deepcopy

def grid_summary(grid):
    """return basic information of the grid
    grid: a PowerGrid object"""
    gen_cap = np.sum(grid.pgmax)
    total_cap = deepcopy(gen_cap)
    default_load = np.sum(grid.load_default)
    
    if grid.no_solar > 0:
        solar_cap = np.sum(grid.solar_default)
        total_cap += solar_cap
    else:
        solar_cap = 0
    if grid.no_wind > 0:
        wind_cap = np.sum(grid.wind_default)
        total_cap += wind_cap
    else:
        wind_cap = 0
    
    print("=========system summary=========")
    print(f"total generator capacity: {gen_cap}")
    print(f"total solar capacity: {solar_cap}")
    print(f"total wind capacity: {wind_cap}")
    print(f"max renewable capacity: {(solar_cap + wind_cap) / total_cap}")
    print(f"max load penetration: {default_load / total_cap}")

def load_grid_from_xlsx(xlsx_path: str, T, reserve, pg_init_ratio = None, ug_init = None):
    """load the grid from the excel file"""
    
    my_grid = Operation(xlsx_path, T, reserve, pg_init_ratio, ug_init)
    
    grid_summary(my_grid)

    return my_grid

# def load_grid_from_config(pypower_case_name: str, config_path, vectorize = False):
#     """
#     load the grid from the pypower case and the extra configurations
#     pypower_case_name: must be a valid pypower case name, see: https://rwl.github.io/PYPOWER/api/
#     config_path: the path to the configuration file
#     """

#     from_pypower(pypower_case_name, config_path) # construct the excel file

#     if vectorize:
#         my_grid = Operation_vector(f"configs/{pypower_case_name}.xlsx")
#     else:
#         my_grid = Operation(f"configs/{pypower_case_name}.xlsx")
    
#     grid_summary(my_grid)

#     return my_grid

def from_pypower(pypower_case_name: str, extra_config_path: str):
    """
    load grid from pypower and add/overwrite the default settings by the new_configs
    extra_config_path: the path to the new configs
    """
    
    print("========= Constructing the grid configuration =========")

    with open(extra_config_path, "r") as f:
        # load the new configurations
        extra_configs = json.load(f)

    def load_grid_pypower(pypower_case_name):
        grid = getattr(api, pypower_case_name)()
        return grid

    configs = load_grid_pypower(pypower_case_name) # pypower case

    """
    empty dataframes
    """
    # construct the dataframes that contains new configurations in addition to the pypower case
    basic = pd.DataFrame(
        columns = ["baseMVA", "slack_idx", "slack_theta"]
        )
    bus = pd.DataFrame(
        columns = ["GS"]
        ) # GS is the shunt conductance
    gen = pd.DataFrame(
        columns = ["idx", "pgmax", "pgmin", 
                    "cf", "cv", "cv2", "csu", "csd", "ces", # cost
                    "ru", "rd", "rsu", "rsd", "rued", "rded"]   # constraint
                                )
    load = pd.DataFrame(
        columns = ["idx", "default", "cls"]
        ) # clshed is the load shedding cost
    branch = pd.DataFrame(
        columns = ["fbus", "tbus", "x", "pfmax", "tap_ratio", "shift_angle"]
        )
    
    # check if solar and wind are present
    with_solar = True if len(extra_configs["solar"]) != 0 else False
    with_wind = True if len(extra_configs["wind"]) != 0 else False
    if with_solar:
        solar = pd.DataFrame(columns = ["idx", "default", "csc"])
        solar["idx"] = extra_configs["solar"]["idx"]
    if  with_wind:
        wind = pd.DataFrame(columns = ["idx", "default",  "cwc"])
        wind["idx"] = extra_configs["wind"]["idx"]
    
    """
    add pypower default settings to the dataframes
    ! all index are 1-based
    """
    # pypower default settings
    basic["baseMVA"] = [configs["baseMVA"]]
    basic["slack_idx"] = [int(np.where(configs["bus"][:, BUS_TYPE] == 3)[0][0] + 1)]
    basic["slack_theta"] = [configs["bus"][basic["slack_idx"][0] - 1, VA]]

    if extra_configs["bus"]["shunt"]:
        bus["GS"] = configs["bus"][:, GS]
    else:
        bus["GS"] = np.zeros(len(configs["bus"]))

    gen["idx"] = configs['gen'][:, GEN_BUS].tolist() # the default index is 1-based
    gen["pgmax"] = configs['gen'][:, PMAX].tolist()
    gen["pgmin"] = configs['gen'][:, PMIN].tolist()
    gen["cv"] = configs['gencost'][:, 5].tolist()
    gen["cv2"] = (configs['gencost'][:, 4] * configs["baseMVA"]).tolist() # match the p.u. conversion

    load_idx = np.where(configs["bus"][:, PD] != 0)[0] + 1
    load["idx"] = load_idx.tolist()
    load["default"] = configs["bus"][load_idx - 1, PD].tolist()

    branch["fbus"] = configs["branch"][:, F_BUS].tolist()
    branch["tbus"] = configs["branch"][:, T_BUS].tolist()
    branch["x"] = configs["branch"][:, BR_X].tolist()
    branch["pfmax"] = configs["branch"][:, RATE_A].tolist()
    for i in range(len(branch)):
        if configs["branch"][i, TAP] == 0: # mathmatically 0 means that the tap ratio is 1
            configs["branch"][i, TAP] = 1
    branch["tap_ratio"] = configs["branch"][:, TAP].tolist()
    branch["shift_angle"] = configs["branch"][:, SHIFT].tolist()

    data_frame = {
        "basic": basic,
        "bus": bus,
        "gen": gen,
        "load": load,
        "branch": branch
    }

    if with_solar:
        data_frame["solar"] = solar
    if with_wind:
        data_frame["wind"] = wind
        
    """
    overwrite the default settings from pypower
    """
    # dictionary of new configurations
    # configs_new = {key: value for key, value in new_configs.items() if key in data_frame.keys()}

    for element_name, element_dict in extra_configs.items():
        if not isinstance(element_dict, dict):
            print(element_name, element_dict)
            continue
        
        for column_name, value in element_dict.items():
            if column_name in data_frame[element_name].columns:
                # already exists in the dataframe constructed by the pypower case
                if isinstance(value, Iterable):
                    if len(value) == len(data_frame[element_name]):
                        data_frame[element_name][column_name] = value
                    elif len(value) == 0:
                        # no element do not overwrite
                        pass
                    elif len(value) == 1:
                        # repeat this value for all elements
                        data_frame[element_name][column_name] = [value[0]] * len(data_frame[element_name])
                    else:
                        raise ValueError(f"Length mismatch for {column_name} in {element_name} in the new configurations")
                else:
                    pass
                    # # the value is scalar
                    # # branch[column_name] = [value] * len(branch)
                    # data_frame[element_name][column_name] = [value] * len(data_frame[element_name])
    
    """
    the new configurations that are not in the pypower case
    """
    # the constraint _ratio entry
    for column_name, value in extra_configs["gen"].items():
        if "ratio" in column_name:
            # with respect to the pgmax
            base_value = data_frame["gen"]["pgmax"]
            column_name_ = column_name.replace("_ratio", "") 
            if column_name_ in data_frame["gen"].columns:
                data_frame["gen"][column_name_] = value * np.array(base_value)
            else:
                raise ValueError(f"Column {column_name} not found in gen")
    
    # the cost _ratio entry
    base_value = np.max(data_frame["gen"]["cv"]) # with respect to the largest variable cost
    data_frame["gen"]["ces"] = base_value * extra_configs["gen"]["ces_ratio"] * np.ones(len(data_frame["gen"]))
    data_frame["load"]["cls"] = base_value * extra_configs["load"]["cls_ratio"] * np.ones(len(data_frame["load"]))
    
    # if "cgstore_ratio" in extra_configs["gen"].keys():
    #     base_value = np.max(data_frame["gen"]["cv"]) # with respect to the largest variable cost
    #     data_frame["gen"]["cgstore"] = base_value * new_configs["gen"]["cgstore_ratio"] * np.ones(len(data_frame["gen"]))
    
    # if "clshed_ratio" in new_configs["load"].keys():
    #     base_value = np.max(new_configs["gen"]["cgv"]) # with respect to the largest variable cost
    #     data_frame["load"]["clshed"] = base_value * new_configs["load"]["clshed_ratio"] * np.ones(len(data_frame["load"]))
    
    """
    renewable entry
    """
    gen_cap = np.sum(data_frame["gen"]["pgmax"])
    total_cap = deepcopy(gen_cap)
    if with_solar:
        data_frame["solar"]["csc"] = base_value * extra_configs["solar"]["csc_ratio"] * np.ones(len(data_frame["solar"]))
        if len(extra_configs["solar"]["default_ratio"]) == 1:
            data_frame["solar"]["default"] = gen_cap * np.array(extra_configs["solar"]["default_ratio"]) * np.ones(len(data_frame["solar"]))
        else:
            data_frame["solar"]["default"] = gen_cap * np.array(extra_configs["solar"]["default_ratio"])
        total_cap += data_frame["solar"]["default"].sum()

    if with_wind:
        data_frame["wind"]["cwc"] = base_value * extra_configs["wind"]["cwc_ratio"] * np.ones(len(data_frame["wind"]))
        if len(extra_configs["wind"]["default_ratio"]) == 1:
            data_frame["wind"]["default"] = gen_cap * np.array(extra_configs["wind"]["default_ratio"]) * np.ones(len(data_frame["wind"]))
        else:
            data_frame["wind"]["default"] = gen_cap * np.array(extra_configs["wind"]["default_ratio"])
        total_cap += data_frame["wind"]["default"].sum()
    
    # rescale the load
    data_frame["load"]["default"] = extra_configs["load"]["max_default_ratio"] * data_frame["load"]["default"] * total_cap / np.sum(data_frame["load"]["default"])
    
    # save to excel
    with pd.ExcelWriter(f"configs/{pypower_case_name}.xlsx", engine='xlsxwriter') as writer:
        for element_name, element_df in data_frame.items():
            element_df.to_excel(writer, sheet_name=element_name, index=False)
    
    no_load = len(data_frame["load"])
    no_solar = len(data_frame["solar"]) if with_solar else 0
    no_wind = len(data_frame["wind"]) if with_wind else 0

    # return no_load, no_solar, no_wind