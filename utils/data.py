"""
clearn the data and construct the dataset
return csv files for each bus including the following columns:

Features (have been normalized for each bus):
    'Weekday_sin', 'Weekday_cos', 'Hour_sin', 'Hour_cos', 'Temperature (k)', 'Shortwave Radiation (w/m2)',
    'Longwave Radiation (w/m2)', 'Zonal Wind Speed (m/s)', 'Meridional Wind Speed (m/s)', 'Wind Speed (m/s)', 
Target (is not normalized)):    
'Load'
"""

import pandas as pd
from tqdm import trange
import numpy as np
import datetime
import os
import time
import shutil


def gen_data(NO_BUS, SAVE_DIR, NORMALIZE_WEATHER = False, WIND_NO = 0, SOLAR_NO = 0, FORECE_NEW = False):

    NO_DAY = 365
    NO_BUS_TOTAL = 123
    NO_HOUR = 24
    print(f'Cleaning data for case NO of {NO_BUS} buses')

    """
    load: into size (365 * 24, NO_BUS_TOTAL)
    """
    load_all = []
    for day in trange(1, NO_DAY+1, desc='Loading load data'):
        load_all.append(pd.read_csv(f'data/Data_public/load_2019/load_annual_D{day}.txt', sep=" ", header=None))
    load_all = pd.concat(load_all, axis=0)
    load_all.reset_index(drop=True, inplace=True)

    # find the no of NO_BUS buses that are most uncorrelated
    load_corr = np.corrcoef(load_all.values.T)
    bus_index_summary = []
    corr_summary = []
    for i in range(NO_BUS_TOTAL):
        bus_index = [i]
        for _ in range(1, NO_BUS):
            summed_corr = np.sum(load_corr[bus_index, :], axis=0) # sum of correlation of all the previous buses
            j = 0
            new_index = np.argsort(summed_corr)[j]
            while new_index in bus_index:
                j += 1
                new_index = np.argsort(summed_corr)[j]
            bus_index.append(new_index)
        
        bus_index_summary.append(bus_index)
        corr = load_corr[bus_index, :][:, bus_index]
        corr_summary.append(corr.mean())

    index = np.argsort(corr_summary)[0]
    BUS_INDEX = bus_index_summary[index] # the selected bus index

    # NOTE: ALL INDEX IS 1-BASED
    BUS_INDEX = [i + 1 for i in BUS_INDEX]

    print(BUS_INDEX)

    """
    wind and solar
    """
    gen_data = pd.read_excel('data/Data_public/Generator_data.xlsx', sheet_name='Gen data')
    wind_data = pd.read_excel('data/Data_public/Generator_data.xlsx', sheet_name='Wind Plant Number')
    solar_data = pd.read_excel('data/Data_public/Generator_data.xlsx', sheet_name='Solar Plant Number')

    # link the wind with the bus
    if WIND_NO > 0:
        wind_to_bus = {}
        for bus in reversed(BUS_INDEX):
            gen_idx = gen_data[gen_data['Bus Number'] == bus].index.values
            gen_idx = [i + 1 for i in gen_idx]
            # pick the wind idx that has Generator Number within the gen_idx
            wind_idx = wind_data[wind_data['Generator Number'].isin(gen_idx)].index.values
            wind_idx = [i + 1 for i in wind_idx]

            if len(wind_idx) > 0:
                wind_to_bus[wind_idx[0]] = bus
            
            if len(wind_to_bus) == WIND_NO:
                break
        
        print('wind_idx to bus_idx:', wind_to_bus)

        # load the wind data
        wind_all = {}
        for wind_idx in wind_to_bus.keys():
            for day in trange(1, NO_DAY+1, desc='Loading wind data'):
                wind = pd.read_csv(f'data/Data_public/wind_2019/wind_annual_D{day}.txt', sep=" ", header=None)
                if wind_idx not in wind_all:
                    wind_all[wind_idx] = wind.iloc[wind_idx-1, :]
                else:
                    wind_all[wind_idx] = pd.concat([wind_all[wind_idx], wind.iloc[wind_idx-1, :]], axis=0, ignore_index=True)
    
    # link the solar with the bus
    if SOLAR_NO > 0:
        solar_to_bus = {}
        for bus in BUS_INDEX:
            gen_idx = gen_data[gen_data['Bus Number'] == bus].index.values
            gen_idx = [i + 1 for i in gen_idx]
            # pick the solar idx that has Generator Number within the gen_idx
            solar_idx = solar_data[solar_data['Generator Number'].isin(gen_idx)].index.values
            solar_idx = [i + 1 for i in solar_idx]

            if len(solar_idx) > 0:
                solar_to_bus[solar_idx[0]] = bus
            
            if len(solar_to_bus) == SOLAR_NO:
                break
        
        print('solar_idx to bus_idx:', solar_to_bus)

        # load the solar data
        solar_all = {}
        for solar_idx in solar_to_bus.keys():
            for day in trange(1, NO_DAY+1, desc='Loading solar data'):
                solar = pd.read_csv(f'data/Data_public/solar_2019/solar_annual_D{day}.txt', sep=" ", header=None)
                if solar_idx not in solar_all:
                    solar_all[solar_idx] = solar.iloc[solar_idx-1,:]
                else:
                    solar_all[solar_idx] = pd.concat([solar_all[solar_idx], solar.iloc[solar_idx-1,:]], axis=0, ignore_index=True)

    """
    weather and calendar data: each bus has a dataframe of size (365 * 24, 10)
    """
    example_df = pd.read_excel("data/Data_public/Climate_2019/climate_2019_Day" + '1.csv', 
                            sheet_name='Hour 1')
    climate_dict = {key: pd.DataFrame(columns=example_df.columns) for key in BUS_INDEX}


    for i in trange(1, NO_DAY+1, desc='Loading climate data'):
        climate_data_all = pd.ExcelFile("data/Data_public/Climate_2019/climate_2019_Day" 
                                        + str(i) + '.csv')
        for hour in [f'Hour {i}' for i in range(1,NO_HOUR+1)]:
            climate_data_per_hour = climate_data_all.parse(hour)
            for index, bus in enumerate(BUS_INDEX):
                if len(climate_dict[bus]) == 0:
                    climate_dict[bus] = climate_data_per_hour.iloc[bus-1:bus]
                else:
                    climate_dict[bus] = pd.concat([climate_dict[bus], climate_data_per_hour.iloc[bus-1:bus]], ignore_index=True, axis=0)

    # remove bus index and normalize the climate data
    for bus in BUS_INDEX:
        climate_dict[bus].drop(columns=['Bus'], inplace=True)
        # standardize 
        if NORMALIZE_WEATHER:
            climate_dict[bus] = (climate_dict[bus] - climate_dict[bus].mean()) / climate_dict[bus].std()

    # add weekday information for each bus
    start_weekday = datetime.datetime(2019,1,1).weekday()
    one_week = np.concatenate([np.arange(start_weekday, 7), (np.arange(0, start_weekday))])

    day = np.repeat(np.arange(1,NO_DAY + 1), 24)
    hour = np.tile(np.arange(1,25), NO_DAY)
    weekday = np.tile(np.repeat(one_week, 24), 53)[:NO_DAY * 24]

    # day_sin = np.sin(2 * np.pi * day / NO_DAY)
    # day_cos = np.cos(2 * np.pi * day / NO_DAY)
    hour_sin = np.sin(2 * np.pi * ( hour / 24))
    hour_cos = np.cos(2 * np.pi * ( hour / 24))
    weekday_sin = np.sin(2 * np.pi * ( weekday / 7))
    weekday_cos = np.cos(2 * np.pi * ( weekday / 7))

    """
    save
    """
    # change the order of the columns
    FEATURE_COLUMNS = ['Weekday_sin', 'Weekday_cos', 'Hour_sin', 'Hour_cos', 'Temperature (k)', 'Shortwave Radiation (w/m2)',
                    'Longwave Radiation (w/m2)', 'Zonal Wind Speed (m/s)',
                    'Meridional Wind Speed (m/s)', 'Wind Speed (m/s)']
    TARGET_COLUMN = ['Load']

    if WIND_NO > 0:
        TARGET_COLUMN += ['Wind']
    if SOLAR_NO > 0:
        TARGET_COLUMN += ['Solar']

    for bus in BUS_INDEX:
        # climate_dict[bus]['Day_sin'] = day_sin
        # climate_dict[bus]['Day_cos'] = day_cos
        climate_dict[bus]['Hour_sin'] = hour_sin
        climate_dict[bus]['Hour_cos'] = hour_cos
        climate_dict[bus]['Weekday_sin'] = weekday_sin
        climate_dict[bus]['Weekday_cos'] = weekday_cos
        climate_dict[bus]['Load'] = load_all.iloc[:,bus-1]

        if WIND_NO > 0:
            climate_dict[bus]['Wind'] = 0
            for wind_idx in wind_to_bus.keys():
                if wind_to_bus[wind_idx] == bus: # if buses match
                    climate_dict[bus]['Wind'] = wind_all[wind_idx]

        if SOLAR_NO > 0:
            climate_dict[bus]['Solar'] = 0
            for solar_idx in solar_to_bus.keys():
                if solar_to_bus[solar_idx] == bus: # if buses match
                    climate_dict[bus]['Solar'] = solar_all[solar_idx]
        
        # change the order of the columns
        climate_dict[bus] = climate_dict[bus][FEATURE_COLUMNS + TARGET_COLUMN]
        climate_dict[bus].reset_index(drop=True, inplace=True)

    if FORECE_NEW:
        if os.path.exists(SAVE_DIR):
            print('force remove all past data')
            shutil.rmtree(SAVE_DIR)
        
        if not os.path.exists(SAVE_DIR):
            print(f'generating directory {SAVE_DIR} and save the data')
            os.makedirs(SAVE_DIR)
        
        for bus in BUS_INDEX:
            climate_dict[bus].to_csv(SAVE_DIR + f'bus_{bus}.csv', index=False)

if __name__ == '__main__':
    
    import argparse

    parser = argparse.ArgumentParser(description='Generate dataset for the given number of buses')
    parser.add_argument('--NO_LOAD', type=int, help='Number of LOAD', default = 11)
    parser.add_argument('--SAVE_DIR', type=str, help='Directory to save the data', default='data/case14/')
    parser.add_argument('--WIND_NO', type=int, help='Number of wind', default=2)
    parser.add_argument('--SOLAR_NO', type=int, help='Number of solar', default=2)
    parser.add_argument('--NORMALIZE_WEATHER', default = False, action='store_true')
    parser.add_argument('--FORCE_NEW', default = False, action='store_true')
    args = parser.parse_args()

    gen_data(args.NO_LOAD, args.SAVE_DIR, args.NORMALIZE_WEATHER, args.WIND_NO, args.SOLAR_NO, args.FORCE_NEW)