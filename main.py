"""
a complete pipeline to construct grid and generate data for case14 system
"""
from utils.group_data import group_data
from utils import from_pypower, assign_data, modify_pfmax, load_grid_from_xlsx


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--pypower_case_name', type=str, default="case14")
    parser.add_argument('-c', '--extra_config_path', type=str, default="configs/case14_default.json")
    parser.add_argument('-f', '--force_new', default = False, action='store_true')
    args = parser.parse_args()
    
    """clean the data"""
    group_data()
    
    """generate the grid"""
    from_pypower(
        pypower_case_name=args.pypower_case_name, 
        extra_config_path=args.extra_config_path
        )
    
    """assign data to load bus"""
    assign_data(
        xlsx_dir = f'configs/{args.pypower_case_name}.xlsx',
        save_dir = f"data/{args.pypower_case_name}/",
        seed = 0,
        force_new = args.force_new
        )
    
    """you can change here"""
    T = 6
    with_int = False
    reserve = 0.0
    pg_init_ratio = 0.5
    ug_init = 1
        
    grid_op = load_grid_from_xlsx(
        xlsx_path = f"configs/{args.pypower_case_name}.xlsx", T = T, 
        reserve = reserve, 
        pg_init_ratio = pg_init_ratio, ug_init = ug_init
        )
    
    modify_pfmax(grid_op, with_int, T, 
                f"data/{args.pypower_case_name}/", 
                min_pfmax = 0.1, 
                scale_factor = 1.2,
                xlsx_dir = f"configs/{args.pypower_case_name}.xlsx",
                force_new = args.force_new)