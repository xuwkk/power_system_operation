import json
from utils import from_pypower
from operation import Operation

def load_grid(pypower_case_name, config_path):

    with open(config_path, "r") as f:
        my_configs = json.load(f)
    from_pypower(pypower_case_name, my_configs)
    my_grid = Operation(f"configs/{pypower_case_name}.xlsx")

    return my_grid