"""
test the data
"""

import pandas as pd
import numpy as np
import os

def test_data(xlsx_path, data_folder):

    load_config = pd.read_excel(xlsx_path, sheet_name='load', engine='openpyxl')
    solar_config = pd.read_excel(xlsx_path, sheet_name='solar', engine='openpyxl')
    wind_config = pd.read_excel(xlsx_path, sheet_name='wind', engine='openpyxl')

    no_load = len(load_config)

    for i in range(1, no_load + 1):
        data = pd.read_csv(os.path.join(data_folder, f"data_{i}.csv"))
        assert np.isclose(np.max(data['Load']), load_config['default'][i - 1], atol=1e-5), f"load {i} value is not correct"
        if data['Solar'].sum() > 0:
            print(f"load {i} has solar")
            bus_idx = load_config['idx'][i - 1] # the bus index of the load
            idx = solar_config[solar_config['idx'] == bus_idx].index.values[0]
            assert np.isclose(np.max(data['Solar']), solar_config['default'][idx], atol=1e-5), f"solar {i} value is not correct"
        if data['Wind'].sum() > 0:
            print(f"load {i} has wind")
            bus_idx = load_config['idx'][i - 1] # the bus index of the load
            idx = wind_config[wind_config['idx'] == bus_idx].index.values[0]
            assert np.isclose(np.max(data['Wind']), wind_config['default'][idx], atol=1e-5), f"wind {i} value is not correct"
    
    print("All data are correct")

if __name__ == "__main__":

    xlsx_path = "configs/case14.xlsx"
    data_folder = "data/case14"

    test_data(xlsx_path, data_folder)