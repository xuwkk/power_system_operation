"""
test the grid matrices Bbus, Bf, Pbusinj, Pfinj are the same to the PyPower results
"""

import sys
import numpy as np
sys.path.append('.')
from utils import load_grid_from_config
from pypower import api

def test_grid_formulation(pypower_case_name, config_path):
    
    my_grid = load_grid_from_config(pypower_case_name, config_path)
    grid_pypower = getattr(api, pypower_case_name)()
    grid_pypower_int = api.ext2int(grid_pypower)

    Bbus, Bf, Pbusinj, Pfinj = api.makeBdc(grid_pypower_int['baseMVA'], 
                                        grid_pypower_int['bus'], 
                                        grid_pypower_int['branch'])
    assert np.allclose(my_grid.Bbus, Bbus.toarray()), "Bbus is not equal to the pypower results, probably due to the overwrite of the tap_ratio"
    assert np.allclose(my_grid.Bf, Bf.toarray()), "Bf is not equal to the pypower results, probably due to the overwrite of the tap_ratio"
    assert np.allclose(my_grid.Pbusshift, Pbusinj), "Pbusinj is not equal to the pypower results"
    assert np.allclose(my_grid.Pfshift, Pfinj), "Pfinj is not equal to the pypower results"

    print('All tests passed')

if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--pypower_case_name', type=str, default="case14")
    parser.add_argument('-c', '--config_path', type=str, default="configs/case14_default.json")
    args = parser.parse_args()

    test_grid_formulation(args.pypower_case_name, config_path=args.config_path)