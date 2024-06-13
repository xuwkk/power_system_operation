import pandas as pd
from collections.abc import Iterable
import numpy as np

class PowerGrid:

    def __init__(self, system_path: str):

        """
        construct the basic power grid
        system_path: the path to the system configuration file, must be an excel file
        """
        
        # read the excel file
        basic = pd.read_excel(system_path, sheet_name="basic", engine='openpyxl')
        bus = pd.read_excel(system_path, sheet_name="bus", engine='openpyxl')
        gen = pd.read_excel(system_path, sheet_name="gen", engine='openpyxl')
        load = pd.read_excel(system_path, sheet_name="load", engine='openpyxl')
        branch = pd.read_excel(system_path, sheet_name="branch", engine='openpyxl')
        try:
            solar = pd.read_excel(system_path, sheet_name="solar", engine='openpyxl')
        except:
            solar = None
        try:
            wind = pd.read_excel(system_path, sheet_name="wind", engine='openpyxl')
        except:
            wind = None

        # no
        self.no_bus = len(bus)
        self.no_gen = len(gen)
        self.no_branch = len(branch)
        self.no_load = len(load)
        self.no_solar = len(solar) if solar is not None else 0
        self.no_wind = len(wind) if wind is not None else 0
        
        # basic
        baseMVA = basic["baseMVA"].values[0]
        self.slack_idx = PowerGrid._to_python_idx(basic["slack_idx"].values[0])
        self.slack_theta = basic["slack_theta"].values[0]

        # gen
        for column in gen.columns:
            if column == "idx":
                self.Cg = np.zeros((self.no_bus, self.no_gen))
                for i in range(self.no_gen):
                    idx = PowerGrid._to_python_idx(gen["idx"][i])
                    self.Cg[idx, i] = 1
            
            # to p.u. on ramp and generation constraints
            elif "rg" in column or "pg" in column:
                setattr(self, column, gen[column].values / baseMVA)
            
            # cost
            else:
                setattr(self, column, gen[column].values)
            
        self.cgv = self.cgv * baseMVA  # !convert to $/p.u.
        
        # load
        self.Cl = np.zeros((self.no_bus, self.no_load))
        for i in range(self.no_load):
            idx = PowerGrid._to_python_idx(load["idx"][i])
            self.Cl[idx, i] = 1
        self.load_default = load["default"].values / baseMVA # to pu
        self.clshed = load["clshed"].values * baseMVA # !convert to $/p.u.
        
        # solar
        if solar is not None:
            self.solar_default = solar["default"].values / baseMVA
            self.csshed = solar["csshed"].values * baseMVA # !convert to $/p.u.
            self.Cs = np.zeros((self.no_bus, self.no_solar))
            for i in range(self.no_solar):
                idx = PowerGrid._to_python_idx(solar["idx"][i])
                self.Cs[idx, i] = 1
        
        # wind
        if wind is not None:
            self.wind_default = wind["default"].values / baseMVA
            self.cwshed = wind["cwshed"].values * baseMVA # !convert to $/p.u.
            self.Cw = np.zeros((self.no_bus, self.no_wind))
            for i in range(self.no_wind):
                idx = PowerGrid._to_python_idx(wind["idx"][i])
                self.Cw[idx, i] = 1
        
        # branch
        Cf = np.zeros((self.no_branch, self.no_bus))
        Ct = np.zeros((self.no_branch, self.no_bus))
        for i in range(self.no_branch):
            fbus = PowerGrid._to_python_idx(branch["fbus"][i])
            tbus = PowerGrid._to_python_idx(branch["tbus"][i])
            Cf[i, fbus] = 1
            Ct[i, tbus] = 1
        self.A = Cf - Ct # bus-to-branch incidence matrix

        Bff = 1/(branch["x"].values * branch["tap_ratio"].values)
        self.Bf = np.diag(Bff) @ self.A # branch susceptance matrix
        self.Bbus = self.A.T @ self.Bf  # bus susceptance matrix
        self.Pfshift = -branch["shift_angle"].values / np.pi * Bff
        self.Pbusshift = self.A.T @ self.Pfshift
        self.Gsh = bus['GS'].values / baseMVA

        self.pfmax = branch["pfmax"].values / baseMVA
    
    @staticmethod
    def _to_python_idx(idx):
        """convert to the 0-based index"""
        if isinstance(idx, Iterable):
            return [int(i) - 1 for i in idx]
        else:
            return int(idx) - 1