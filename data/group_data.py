"""
group the original data into each data csv file
"""

import pandas as pd
from tqdm import trange
import numpy as np
import datetime
import os

def return_renewable_incidences(no_bus):

    # link the generator idx to the bus idx
    # one bus can have multiple gen
    gen_data = pd.read_excel('data/Data_public/Generator_data.xlsx', sheet_name='Gen data')    
    # link the solar idx to the gen idx
    solar_data = pd.read_excel('data/Data_public/Generator_data.xlsx', sheet_name='Solar Plant Number')
    # link the wind idx to the gen idx
    wind_data = pd.read_excel('data/Data_public/Generator_data.xlsx', sheet_name='Wind Plant Number')

    bus_to_gen = {}
    for bus_idx in range(1, no_bus+1):
        gen_idx = gen_data[gen_data['Bus Number'] == bus_idx]['Gen Number'].values  # ! only consider one generator per bus
        if len(gen_idx) == 0:
            bus_to_gen[bus_idx] = 0
        else:
            bus_to_gen[bus_idx] = gen_idx.tolist()

    solar_to_bus = {}
    wind_to_bus = {}
    for bus_idx, gen_idx in bus_to_gen.items():
        if gen_idx != 0:
            for idx in gen_idx:
                solar_idx = solar_data[solar_data['Generator Number'] == idx]['Solar Plant Number'].values
                wind_idx = wind_data[wind_data['Generator Number'] == idx]['Wind Plant Number'].values

                # only assign one solar or wind to one bus
                if len(solar_idx) != 0:
                    solar_to_bus[solar_idx[0]] = bus_idx
                    break
                if len(wind_idx) != 0:
                    wind_to_bus[wind_idx[0]] = bus_idx
                    break
    
    return solar_to_bus, wind_to_bus

def group_data():

    print("========= Grouping data =========")

    no_bus = 123
    no_day = 365
    no_hour = 24
    
    # empty dataframes
    climate_hour = pd.read_excel("data/Data_public/Climate_2019/climate_2019_Day" + '1.csv', sheet_name='Hour 1')
    data_all = {key: pd.DataFrame(columns=climate_hour.columns) for key in range(1, no_bus+1)}

    # climate data
    for i in trange(1, no_day+1, desc='Loading climate data'):
        climate_data_day = pd.ExcelFile("data/Data_public/Climate_2019/climate_2019_Day" + str(i) + '.csv')
        for hour in [f'Hour {i}' for i in range(1,no_hour+1)]:
            climate_data_hour = climate_data_day.parse(hour)
            for bus_idx in range(1, no_bus +1):
                if len(data_all[bus_idx]) == 0:
                    data_all[bus_idx] = climate_data_hour.iloc[bus_idx-1:bus_idx]
                else:
                    data_all[bus_idx] = pd.concat([data_all[bus_idx], climate_data_hour.iloc[bus_idx-1:bus_idx]], ignore_index=True, axis=0)

    # load data
    load_all = []
    for day in trange(1, no_day+1, desc='Loading load data'):
        load_all.append(pd.read_csv(f'data/Data_public/load_2019/load_annual_D{day}.txt', sep=" ", header=None))
    load_all = pd.concat(load_all, axis=0)  # (no_day*no_hour, no_bus)
    load_all.reset_index(drop=True, inplace=True)
    for bus_idx in range(1, no_bus+1):
        data_all[bus_idx]['Load'] = load_all[bus_idx-1]
    
    # solar and wind incidence matrix
    solar_to_bus, wind_to_bus = return_renewable_incidences(no_bus)
    
    # add new columns
    for idx, data in data_all.items():
        data['Solar'] = 0
        data['Wind'] = 0
    
    # pack the solar
    solar_all = {solar_idx: [] for solar_idx in solar_to_bus.keys()}
    for day in trange(1, no_day+1, desc='Loading solar data'):
        solar_day = pd.read_csv(f'data/Data_public/solar_2019/solar_annual_D{day}.txt', sep=" ", header=None)
        for solar_idx in solar_to_bus.keys():
            if len(solar_all[solar_idx]) == 0:
                solar_all[solar_idx] = solar_day.iloc[solar_idx-1,:]
            else:
                solar_all[solar_idx] = pd.concat([solar_all[solar_idx], solar_day.iloc[solar_idx-1,:]], axis=0, ignore_index=True)
    
    # assign solar to data
    for solar_idx, bus_idx in solar_to_bus.items():
        data_all[bus_idx]['Solar'] = solar_all[solar_idx]

    # pack the wind
    wind_all = {wind_idx: [] for wind_idx in wind_to_bus.keys()}
    for day in trange(1, no_day+1, desc='Loading wind data'):
        wind_day = pd.read_csv(f'data/Data_public/wind_2019/wind_annual_D{day}.txt', sep=" ", header=None)
        for wind_idx in wind_to_bus.keys():
            if len(wind_all[wind_idx]) == 0:
                wind_all[wind_idx] = wind_day.iloc[wind_idx-1, :]
            else:
                wind_all[wind_idx] = pd.concat([wind_all[wind_idx], wind_day.iloc[wind_idx-1, :]], axis=0, ignore_index=True)
    
    # assign wind to data
    for wind_idx, bus_idx in wind_to_bus.items():
        data_all[bus_idx]['Wind'] = wind_all[wind_idx]
    
    print('solar to bus:', solar_to_bus, 'length:', len(solar_to_bus))
    print('wind to bus:', wind_to_bus, 'length:', len(wind_to_bus))

    # add calender data
    start_weekday = datetime.datetime(2019,1,1).weekday()
    one_week = np.concatenate([np.arange(start_weekday, 7), (np.arange(0, start_weekday))])

    day = np.repeat(np.arange(1,no_day + 1), 24)
    hour = np.tile(np.arange(1,25), no_day)
    weekday = np.tile(np.repeat(one_week, 24), 53)[:no_day * 24]

    hour_sin = np.sin(2 * np.pi * ( hour / 24))
    hour_cos = np.cos(2 * np.pi * ( hour / 24))
    weekday_sin = np.sin(2 * np.pi * ( weekday / 7))
    weekday_cos = np.cos(2 * np.pi * ( weekday / 7))

    for bus in range(1, no_bus+1):
        data_all[bus]['Hour_sin'] = hour_sin
        data_all[bus]['Hour_cos'] = hour_cos
        data_all[bus]['Weekday_sin'] = weekday_sin
        data_all[bus]['Weekday_cos'] = weekday_cos
        data_all[bus]['Load'] = load_all.iloc[:,bus-1]
    
    # change the order of the columns
    columns = ['Weekday_sin', 'Weekday_cos', 'Hour_sin', 'Hour_cos', 'Temperature (k)', 'Shortwave Radiation (w/m2)',
                    'Longwave Radiation (w/m2)', 'Zonal Wind Speed (m/s)',
                    'Meridional Wind Speed (m/s)', 'Wind Speed (m/s)',
                    'Load', 'Solar', 'Wind']
    
    # save the data
    save_dir = 'data/data_grouped'
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    for bus, data in data_all.items():
        data = data[columns]
        data.to_csv(f'data/data_grouped/bus_{bus}.csv', index=False)
    
    np.save('data/data_grouped/solar_to_bus.npy', solar_to_bus, allow_pickle=True)
    np.save('data/data_grouped/wind_to_bus.npy', wind_to_bus, allow_pickle=True)

if __name__ == "__main__":

    group_data()