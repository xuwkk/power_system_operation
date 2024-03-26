from pypower import api
import numpy as np
import pandas as pd
from .pypower_idx import *
from collections.abc import Iterable

def load_grid(pypower_case_name):
    grid = getattr(api, pypower_case_name)()
    return grid

def from_pypower(pypower_case_name: str, new_configs: dict):

    configs = load_grid(pypower_case_name)

    basic = pd.DataFrame(columns = ["baseMVA", "slack_idx", "slack_theta"])
    bus = pd.DataFrame(columns = ["GS"])
    gen = pd.DataFrame(
        columns = ["idx", "pgmax", "pgmin", 
                    "cgf", "cgv", "cgsu", "cgsd", "cgstore", 
                    "rgu", "rgd", "rgsu", "rgsd"]
                                )
    load = pd.DataFrame(columns = ["idx", "default", "clshed"])
    branch = pd.DataFrame(columns = ["fbus", "tbus", "x", "pfmax", "tap_ratio", "shift_angle"])
    
    # check if solar and wind are present
    with_solar = True if "solar" in new_configs.keys() else False
    with_wind = True if "wind" in new_configs.keys() else False
    if with_solar:
        solar = pd.DataFrame(columns = ["idx", "default", "csshed"])
        solar["idx"] = new_configs["solar"]["idx"]
    if  with_wind:
        wind = pd.DataFrame(columns = ["idx", "default",  "cwshed"])
        wind["idx"] = new_configs["wind"]["idx"]
    
    # pypower default settings
    basic["baseMVA"] = [configs["baseMVA"]]
    basic["slack_idx"] = [int(np.where(configs["bus"][:, BUS_TYPE] == 3)[0][0] + 1)]
    basic["slack_theta"] = [configs["bus"][basic["slack_idx"][0] - 1, VA]]

    if new_configs["bus"]["shunt"]:
        bus["GS"] = configs["bus"][:, GS]
    else:
        bus["GS"] = np.zeros(len(configs["bus"]))

    gen["idx"] = configs['gen'][:, GEN_BUS].tolist() 
    gen["pgmax"] = configs['gen'][:, PMAX].tolist()
    gen["pgmin"] = configs['gen'][:, PMIN].tolist()

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

    # add/overwrite default settings by kwargs
    configs_new = {key: value for key, value in new_configs.items() if key in data_frame.keys()}

    for element_name, element_dict in configs_new.items():
        for column_name, value in element_dict.items():
            if column_name in data_frame[element_name].columns:
                if isinstance(value, Iterable):
                    if len(value) == len(data_frame[element_name]):
                        data_frame[element_name][column_name] = value
                    elif len(value) == 0:
                        pass
                    elif len(value) == 1:
                        data_frame[element_name][column_name] = [value[0]] * len(data_frame[element_name])
                    else:
                        raise ValueError(f"Length mismatch for {column_name} in {element_name}")
                else:
                    branch[column_name] = [value] * len(branch)
    
    # the constrait _ratio entry
    for column_name, value in new_configs["gen"].items():
        if "ratio" in column_name:
            base_value = data_frame["gen"]["pgmax"]
            column_name_ = column_name.replace("_ratio", "") 
            if column_name_ in data_frame["gen"].columns:
                data_frame["gen"][column_name_] = value * np.array(base_value)
            else:
                raise ValueError(f"Column {column_name} not found in gen")
    
    # the cost _ratio entry
    if "cgstore_ratio" in new_configs["gen"].keys():
        base_value = np.max(data_frame["gen"]["cgv"])
        data_frame["gen"]["cgstore"] = base_value * new_configs["gen"]["cgstore_ratio"] * np.ones(len(data_frame["gen"]))
    
    if "clshed_ratio" in new_configs["load"].keys():
        base_value = np.max(new_configs["gen"]["cgv"])
        data_frame["load"]["clshed"] = base_value * new_configs["load"]["clshed_ratio"] * np.ones(len(data_frame["load"]))
    
    if "csshed_ratio" in new_configs["solar"].keys() and with_solar:
        base_value = np.max(new_configs["gen"]["cgv"])
        data_frame["solar"]["csshed"] = base_value * new_configs["solar"]["csshed_ratio"] * np.ones(len(data_frame["solar"]))
    
    if "cwshed_ratio" in new_configs["wind"].keys() and with_wind:
        base_value = np.max(new_configs["gen"]["cgv"])
        data_frame["wind"]["cwshed"] = base_value * new_configs["wind"]["cwshed_ratio"] * np.ones(len(data_frame["wind"]))

    # save to excel
    with pd.ExcelWriter(f"configs/{pypower_case_name}.xlsx", engine='xlsxwriter') as writer:
        for element_name, element_df in data_frame.items():
            element_df.to_excel(writer, sheet_name=element_name, index=False)