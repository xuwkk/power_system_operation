from .power_grid import PowerGrid
import cvxpy as cp
import numpy as np

class Operation(PowerGrid):

    def __init__(self, system_path: str):
        """
        formulate the power grid operation problem
        inherit from the PowerGrid class
        system_path: the path to the system configuration file, must be an excel file
        todo: for ed problem, should we use 2D array or 1D array
        """
        super().__init__(system_path)
    
    """
    constraints
    """
    def _flow_constraint(self, T, constraints, theta):

        if T == 1:
            constraints += [
                self.Bf @ theta + self.Pfshift <= self.pfmax, 
                self.Bf @ theta + self.Pfshift >= -self.pfmax
            ]
        else:
            for t in range(T):
                constraints += [
                    self.Bf @ theta[t] + self.Pfshift <= self.pfmax, 
                    self.Bf @ theta[t] + self.Pfshift >= -self.pfmax
                ]
        return constraints
    
    def _power_balance_constraint(self, T, constraints, theta, pg, load, ls, 
                                solar = None, solarc = None, wind = None, windc = None):
        
        if T == 1:
            generation = self.Cg @ pg
            if self.no_solar > 0:
                generation += self.Cs @ (solar - solarc)
            if self.no_wind > 0:
                generation += self.Cw @ (wind - windc)
            
            constraints += [
                self.Bbus @ theta + self.Pbusshift == generation - self.Cl @ (load - ls)
            ]
        else:
            for t in range(T):
                generation = self.Cg @ pg[t]
                if self.no_solar > 0:
                    generation += self.Cs @ (solar[t] - solarc[t])
                if self.no_wind > 0:
                    generation += self.Cw @ (wind[t] - windc[t])
                
                constraints += [
                    self.Bbus @ theta[t] + self.Pbusshift == generation - self.Cl @ (load[t] - ls[t])
                ]
        return constraints
    
    def _slack_constraints(self, T, constraints, theta):
        if T == 1:
            constraints += [theta[self.slack_idx] == self.slack_theta]
        else:
            constraints += [theta[:, self.slack_idx] == self.slack_theta]
        return constraints
    
    def _variable_constraints(self, T, constraints, load, ls, solar = None, solarc = None, wind = None, windc = None):
        
        if T == 1:
            constraints += [ls >= 0, ls <= load]
            if self.no_solar > 0:
                constraints += [solarc >= 0, solarc <= solar]
            if self.no_wind > 0:
                constraints += [windc >= 0, windc <= wind]
        else:
            for t in range(T):
                constraints += [ls[t] >= 0, ls[t] <= load[t]]
                if self.no_solar > 0:
                    constraints += [solarc[t] >= 0, solarc[t] <= solar[t]]
                if self.no_wind > 0:
                    constraints += [windc[t] >= 0, windc[t] <= wind[t]]

        return constraints
    
    def ncuc_no_int(self, T: int = 24):

        # formulate network constrained unit commitment (ncuc) without integer variable

        # parameter and variable
        load = cp.Parameter((T, self.no_load), name = 'load')              # load forecast (T, no_load)
        pg_init = cp.Parameter((self.no_gen), name = 'pg_init')                 # initial generation (no_gen)
        reserve = cp.Parameter((T), name = 'reserve')         # reserve requirement (T,)
            
        pg = cp.Variable((T, self.no_gen), name = 'pg')                    # generation (T, no_gen)
        theta = cp.Variable((T, self.no_bus), name = 'theta')              # phase angle (T, no_bus)
        ls = cp.Variable((T, self.no_load), name = 'ls')                   # load shed (T, no_load)
        
        if self.no_solar > 0:
            solar = cp.Parameter((T, self.no_solar), name = 'solar')
            solarc = cp.Variable((T, self.no_solar), name = 'solarc')      # solar curtailment (T, no_solar)
        if self.no_wind > 0:
            wind = cp.Parameter((T, self.no_wind), name = 'wind')
            windc = cp.Variable((T, self.no_wind), name = 'windc')
        
        # objective function
        obj = 0
        for t in range(T):
            obj += cp.scalar_product(self.cgv, pg[t])              # generation cost
            obj += cp.scalar_product(self.clshed, ls[t])           # load shed cost
            if self.no_solar > 0:
                obj += cp.scalar_product(self.csshed, solarc[t])
            if self.no_wind > 0:
                obj += cp.scalar_product(self.cwshed, windc[t])
        
        # constraints
        constraints = []
        for t in range(T):
            constraints += [pg[t] <= self.pgmax, pg[t] >= self.pgmin]
        
        # ramp limit
        for t in range(1, T):
            constraints += [pg[t] - pg[t-1] <= self.rgu,
                            pg[t] - pg[t-1] >= -self.rgd]
        constraints += [pg[0] - pg_init <= self.rgu,
                        pg[0] - pg_init >= -self.rgd] # initial ramp limit

        # branch flow limit
        constraints = self._flow_constraint(T, constraints=constraints, theta=theta)
        
        # power balance
        constraints = self._power_balance_constraint(T, 
                                                    constraints=constraints, 
                                                    theta=theta, 
                                                    pg=pg, 
                                                    load=load, 
                                                    ls=ls, 
                                                    solar = solar if self.no_solar > 0 else None, solarc = solarc if self.no_solar > 0 else None,
                                                    wind = wind if self.no_wind > 0 else None, windc = windc if self.no_wind > 0 else None
                                                    )

        # slack bus angle
        constraints = self._slack_constraints(T, constraints=constraints, theta=theta)

        # reserve requirement
        # todo: consider area
        for t in range(T):
            constraints += [
                np.sum(self.pgmax) >= cp.sum(pg[t]) + reserve[t]
            ]

        # constraints on the decision variables
        constraints = self._variable_constraints(T,
                                                constraints=constraints, 
                                                load=load, 
                                                ls=ls, 
                                                solar = solar if self.no_solar > 0 else None, solarc = solarc if self.no_solar > 0 else None,
                                                wind = wind if self.no_wind > 0 else None, windc = windc if self.no_wind > 0 else None
                                                )
        
        # formulate the problem
        problem = cp.Problem(cp.Minimize(obj), constraints)

        return problem

    def ncuc_with_int(self, T: int = 24):
        
        # formulate network constrained unit commitment (ncuc) with integer variable

        # parameter and variable
        load = cp.Parameter((T, self.no_load), name = 'load')                   # load forecast (T, no_load)
        pg_init = cp.Parameter((self.no_gen), name = 'pg_init')                 # initial generation (no_gen)
        ug_init = cp.Parameter((self.no_gen), boolean = True, name = 'ug_init') # initial commitment status (no_gen)
        reserve = cp.Parameter((T), name = 'reserve')                           # reserve requirement (T,)
            
        pg = cp.Variable((T, self.no_gen), name = 'pg')                    # generation (T, no_gen)
        ug = cp.Variable((T, self.no_gen), boolean = True, name = 'ug')    # commitment status (T, no_gen)
        yg = cp.Variable((T, self.no_gen), boolean = True, name = 'yg')                    # start-up status (T, no_gen)
        zg = cp.Variable((T, self.no_gen), boolean = True, name = 'zg')                    # shut-down status (T, no_gen)
        theta = cp.Variable((T, self.no_bus), name = 'theta')              # phase angle (T, no_bus)
        ls = cp.Variable((T, self.no_load), name = 'ls')                   # load shed (T, no_load)
        
        if self.no_solar > 0:
            solar = cp.Parameter((T, self.no_solar), name = 'solar')
            solarc = cp.Variable((T, self.no_solar), name = 'solarc')      # solar curtailment (T, no_solar)
        if self.no_wind > 0:
            wind = cp.Parameter((T, self.no_wind), name = 'wind')
            windc = cp.Variable((T, self.no_wind), name = 'windc')
        
        # objective function
        obj = 0
        for t in range(T):
            obj += cp.scalar_product(self.cgf, ug[t])              # generator fixed cost
            obj += cp.scalar_product(self.cgv, pg[t])              #  generator varying cost
            obj += cp.scalar_product(self.cgsu, yg[t])             # start-up cost
            obj += cp.scalar_product(self.cgsd, zg[t])             # shut-down cost
            obj += cp.scalar_product(self.clshed, ls[t])           # load shed cost
            if self.no_solar > 0:
                obj += cp.scalar_product(self.csshed, solarc[t])   # solar curtailment cost
            if self.no_wind > 0: 
                obj += cp.scalar_product(self.cwshed, windc[t])    # wind curtailment cost
        
        # constraints
        constraints = []
        # constraint with initial condition involved
        for t in range(1,T):
            # on-off
            constraints += [yg[t] - zg[t] == ug[t] - ug[t-1]]  # commitment status
            # ramp up
            constraints += [
                pg[t] - pg[t-1] <= cp.multiply(self.rgu, ug[t-1]) + cp.multiply(self.rgsu, yg[t])
            ]
            # ramp down
            # ! ug[t]
            constraints += [
                pg[t-1] - pg[t] <= cp.multiply(self.rgd, ug[t]) + cp.multiply(self.rgsd, zg[t])
            ]
        
        constraints += [yg[0] - zg[0] == ug[0] - ug_init]      
        constraints += [
            pg[0] - pg_init <= cp.multiply(self.rgu, ug_init) + cp.multiply(self.rgsu, yg[0])
        ]
        constraints += [
            pg_init - pg[0] <= cp.multiply(self.rgd, ug[0]) + cp.multiply(self.rgsd, zg[0])
        ]

        # constraint without initial condition involved
        for t in range(T):
            # on-off
            constraints += [yg[t] + zg[t] <= 1]
            # generation limit
            constraints += [pg[t] <= cp.multiply(self.pgmax, ug[t]), pg[t] >= cp.multiply(self.pgmin, ug[t])]

            # constraints += [
            #     pg[t-1] - pg[t] <= cp.multiply(self.rgd, ug[t]) + cp.multiply(self.rgsd, zg[t])
            # ]
        
        constraints = self._flow_constraint(T, constraints=constraints, theta=theta)

        constraints = self._power_balance_constraint(T, constraints=constraints, 
                                                    theta=theta, 
                                                    pg=pg, 
                                                    load=load, 
                                                    ls=ls, 
                                                    solar=solar if self.no_solar > 0 else None, solarc=solarc if self.no_solar > 0 else None,
                                                    wind=wind if self.no_wind > 0 else None, windc=windc if self.no_wind > 0 else None
                                                    )
        
        constraints = self._slack_constraints(T, constraints=constraints, theta=theta)

        # reserve requirement: related to the on-off condition
        for t in range(T):
            constraints += [
                cp.sum(cp.multiply(self.pgmax, ug[t])) >= cp.sum(pg[t]) + reserve[t]
            ]

        # constraints about load shedding
        constraints = self._variable_constraints(T, constraints=constraints, 
                                                load=load, 
                                                ls=ls, 
                                                solar=solar if self.no_solar > 0 else None, solarc=solarc if self.no_solar > 0 else None,
                                                wind=wind if self.no_wind > 0 else None, windc=windc if self.no_wind > 0 else None
                                                )
        
        # formulate the problem
        problem = cp.Problem(cp.Minimize(obj), constraints)
        
        return problem
    
    def ed(self):

        # formulate economic dispatch (ed)
        ug = cp.Parameter((self.no_gen), boolean = True, name = 'ug') # commitment status (no_gen)

        # parameter
        load = cp.Parameter((self.no_load), name = 'load')                   # load forecast (no_load)
        pg = cp.Parameter((self.no_gen), name = 'pg')                        # generation (no_gen) given by the uc

        # variable
        delta_pg = cp.Variable((self.no_gen), name = 'delta_pg')        # generation (no_gen)
        theta = cp.Variable((self.no_bus), name = 'theta')              # phase angle (no_bus)
        ls = cp.Variable((self.no_load), name = 'ls')                   # load shed (no_load)

        if self.no_solar > 0:
            solar = cp.Parameter((self.no_solar), name = 'solar')
            solarc = cp.Variable((self.no_solar), name = 'solarc')
        if self.no_wind > 0:
            wind = cp.Parameter((self.no_wind), name = 'wind')
            windc = cp.Variable((self.no_wind), name = 'windc')

        # objective function
        obj = 0
        obj += cp.scalar_product(self.cgv, delta_pg)              # generator varying cost
        obj += cp.scalar_product(self.clshed, ls)                 # load shed cost
        if self.no_solar > 0:
            obj += cp.scalar_product(self.csshed, solarc)
        if self.no_wind > 0:
            obj += cp.scalar_product(self.cwshed, windc)
        
        # constraints
        constraints = []
        # generation limit
        constraints += [pg + delta_pg <= cp.multiply(self.pgmax, ug), pg + delta_pg >= cp.multiply(self.pgmin, ug)]

        # ramp limit
        constraints += [delta_pg <= self.rgu, delta_pg >= -self.rgd]

        # branch flow limit
        constraints = self._flow_constraint(1, constraints=constraints, theta=theta)

        # power balance
        constraints = self._power_balance_constraint(1, constraints=constraints, 
                                                    theta=theta, 
                                                    pg=pg + delta_pg, 
                                                    load=load, 
                                                    ls=ls, 
                                                    solar=solar if self.no_solar > 0 else None, solarc=solarc if self.no_solar > 0 else None,
                                                    wind=wind if self.no_wind > 0 else None, windc=windc if self.no_wind > 0 else None
                                                    )
        
        # slack bus angle
        constraints = self._slack_constraints(1, constraints=constraints, theta=theta)

        # constraints about load shedding
        constraints = self._variable_constraints(1, constraints=constraints, 
                                                load=load, 
                                                ls=ls, 
                                                solar=solar if self.no_solar > 0 else None, solarc=solarc if self.no_solar > 0 else None,
                                                wind=wind if self.no_wind > 0 else None, windc=windc if self.no_wind > 0 else None
                                                )
        
        # formulate the problem
        problem = cp.Problem(cp.Minimize(obj), constraints)

        return problem

    def get_pf(self, theta):

        # calculate the power flow
        return theta @ self.Bf.T  + self.Pfshift.reshape(1, -1)
    
    @staticmethod
    def solve(prob, parameters: dict, verbose: bool = False, solver: str = 'GUROBI'):
        """
        assign parameter and solve the problem
        the keys of the parameters should be the same as the parameter names in the problem
        """
        for param in prob.parameters():
            try:
                param.value = parameters[param.name()]
            except:
                raise ValueError('Parameter name not found in the problem')
            
        prob.solve(solver = getattr(cp, solver.upper()), verbose = verbose)
    
    @staticmethod  
    def get_sol(prob):
        """
        clean the output into a dictionary
        """
        sol = {}
        for var in prob.variables():
            sol[var.name()] = var.value
        
        return sol