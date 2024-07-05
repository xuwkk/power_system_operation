"""
a complete pipeline to construct grid and generate data for case14 system
"""
from utils import from_pypower, assign_data

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--pypower_case_name', type=str, default="case14")
    parser.add_argument('-c', '--config_path', type=str, default="configs/case14_default.json")
    parser.add_argument('-f', '--force_new', default = False, action='store_true')
    args = parser.parse_args()
    
    no_load, no_solar, no_wind = from_pypower(
        pypower_case_name=args.pypower_case_name, 
        config_path=args.config_path
        )
    
    print('no load:', no_load, 'no solar:', no_solar, 'no wind:', no_wind)

    assign_data(
        xlsx_dir = 'configs/case14.xlsx',
        no_load = no_load, 
        no_solar = no_solar, 
        no_wind = no_wind,
        save_dir = "data/" + args.pypower_case_name + "/",
        seed = 0,
        force_new = args.force_new
        )

    # save_dir = "data/" + args.pypower_case_name + "/"

    # # collect the raw data
    # gen_data(NO_BUS=no_load, SAVE_DIR=save_dir, NORMALIZE_WEATHER=args.normalize_weather,
    #                     SOLAR_NO=no_solar, WIND_NO=no_wind, FORCE_NEW=args.force_new)
    
    # # assign data to load
    # assign_data_to_load(system_path = f"configs/{args.pypower_case_name}.xlsx", 
    #                     data_path = save_dir)