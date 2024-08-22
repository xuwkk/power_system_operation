from .power_grid import PowerGrid
import cvxpy as cp
import numpy as np

class Operation(PowerGrid):

    def __init__(self, system_path: str, T, reserve, pg_init_ratio = None, ug_init = None):
        """
        formulate the power grid operation problem
        inherit from the PowerGrid class
        system_path: the path to the system configuration file, must be an excel file
        reserve: the array of reserve with length of T or a scalar for single step
        pg_init: the initial pg with length of pg, does not need for single step
        ug_init: the initial ug with legnth of R, does not need for single step
        
        1. ncuc_no_int: T = 1 or T > 1
        2. ncuc_with_int: T = 1 or T > 1
        3. ed: T = 1 or T > 1

        comment on the format:
        1. we take the vectorized form for all the variables and parameters, 
        and then use the trick to transpose the vectors to the matrix form 
        so that we dont need to use the for loop for tedious indexing
        
        2. for the case T = 1, we add an additional dimension to the vectorized form 
        so that we can use the same code for both cases.

        todo: solve this issue
        NOTE: the variables with second-order cost is always formulated in vector form.
            otherwise the standard QP will generate extra dummy variables
        """

        super().__init__(system_path)

        self.T = T
        self.reserve = reserve * np.ones(T)      # system-level reserve
        self.first_order_coeff = np.tile(self.cv, T)
        self.second_order_coeff = np.diag(np.tile(self.cv2, T))
        
        if self.T > 1:
            assert pg_init_ratio is not None, "pg_init_ratio is required for T > 1"
            assert ug_init is not None, "ug_init is required for T > 1"
            self.pg_init = self.pgmax * pg_init_ratio
            self.ug_init = ug_init * np.ones(self.no_gen)
            
    def get_opt(self, with_int):
        """return the optimization problem"""
        if with_int:
            return self.ncuc_with_int(), self.ed(with_int)
        else:
            return self.ncuc_no_int(), self.ed(with_int)
    
    def _flow_constraint(self, constraints, theta):
        """theta is a matrix
        for T = 1, theta is a (1, no) matrix, the same in the followings"""

        for t in range(self.T):
            constraints += [
                self.Bf @ theta[t] + self.Pfshift <= self.pfmax, 
                self.Bf @ theta[t] + self.Pfshift >= -self.pfmax
            ]
        return constraints
    
    def _power_balance_constraint(self, constraints, theta, pg_all, 
                                load_all, solar_all = None, wind_all = None):
        
        """
        pg_all = pg - es (for ed) or pg (for ncuc)
        load_all = load - ls
        solar_all = solar - solarc
        wind_all = wind - windc
        
        a vector if T = 1 and a matrix of (T, no) if T > 1
        """
        
        for t in range(self.T):
            generation = self.Cg @ pg_all[t]
            if self.no_solar > 0:
                generation += self.Cs @ solar_all[t]
            if self.no_wind > 0:
                generation += self.Cw @ wind_all[t]
            constraints += [
                self.Bbus @ theta[t] + self.Pbusshift == generation - self.Cl @ load_all[t]
            ]
        return constraints
    
    def _slack_constraints(self, constraints, theta):
        constraints += [theta[:, self.slack_idx] == self.slack_theta]
        return constraints
    
    def _variable_constraints(self, constraints, load, ls, pg = None, es = None,
                            solar = None, solarc = None, wind = None, windc = None):
        """bounds on the penalization variables"""

        for t in range(self.T):
            constraints += [ls[t] >= 0, ls[t] <= load[t]]
            if pg is not None:
                constraints += [es[t] >= 0, es[t] <= pg[t]]
            if self.no_solar > 0:
                constraints += [solarc[t] >= 0, solarc[t] <= solar[t]]
            if self.no_wind > 0:
                constraints += [windc[t] >= 0, windc[t] <= wind[t]]

        return constraints

    def ncuc_no_int(self):
        """formulate network constrained unit commitment (ncuc) without integer variable,
        always in the vectorize form
        ncuc does not contain the energy storage (es) variable
        when T = 1, there is no ramp constaints"""
        
        # the parameter and variable are in vector form
        load = cp.Parameter((self.T * self.no_load), name = 'load')              # load forecast (T * no_load)
        pg = cp.Variable((self.T * self.no_gen), name = 'pg')                    # generation (T * no_gen)
        theta = cp.Variable((self.T * self.no_bus), name = 'theta')              # phase angle (T * no_bus)
        ls = cp.Variable((self.T * self.no_load), name = 'ls')                   # load shed (T * no_load)
        
        # reshape: so that the following formulations are the same for vectorize and matrix form
        load = cp.reshape(load, (self.T, -1), 'C')
        # pg = cp.reshape(pg, (self.T, -1), 'C')
        theta = cp.reshape(theta, (self.T, -1), 'C')
        ls = cp.reshape(ls, (self.T, -1), 'C')
        
        if self.no_solar > 0:
            solar = cp.Parameter((self.T * self.no_solar), name = 'solar')       # solar forecast (T * no_solar)
            solarc = cp.Variable((self.T * self.no_solar), name = 'solarc')      # solar curtailment (T * no_solar)
            solar = cp.reshape(solar, (self.T, -1), 'C')
            solarc = cp.reshape(solarc, (self.T, -1), 'C')
        
        if self.no_wind > 0:
            wind = cp.Parameter((self.T * self.no_wind), name = 'wind')          # wind forecast (T * no_wind)
            windc = cp.Variable((self.T * self.no_wind), name = 'windc')         # wind curtailment (T * no_wind)
            wind = cp.reshape(wind, (self.T, -1), 'C')
            windc = cp.reshape(windc, (self.T, -1), 'C')
        
        """ objective function """
        obj = 0
        # ! to avoid the dummy variable in the standard form
        
        obj += cp.scalar_product(self.first_order_coeff, pg)                   # generation cost
        obj += 0.5 * cp.quad_form(pg, self.second_order_coeff)                # quadratic cost
        
        pg = cp.reshape(pg, (self.T, -1), 'C') # reshape
        
        for t in range(self.T):
            # obj += cp.scalar_product(self.cv, pg[t])                   # generation cost
            # obj += 0.5 * cp.quad_form(pg[t], np.diag(self.cv2))        # quadratic cost
            obj += cp.scalar_product(self.cls, ls[t])                   # load shed cost
            if self.no_solar > 0:
                obj += cp.scalar_product(self.csc, solarc[t])
            if self.no_wind > 0:
                obj += cp.scalar_product(self.cwc, windc[t])
        
        # # ! treat the quadratic cost always in vector form
        # # this may solve the gurobi failure issue and the dummy variable in standard form
        # obj += cp.scalar_product(self.penalty, ls)
        # obj += 0.5 * cp.quad_form(ls, np.diag(self.penalty))
        
        """ constraints """
        constraints = []
        for t in range(self.T):
            constraints += [pg[t] <= self.pgmax, pg[t] >= self.pgmin]
        
        # branch flow limit
        constraints = self._flow_constraint(constraints=constraints, theta=theta)
        
        # power balance
        constraints = self._power_balance_constraint(
                    constraints=constraints, 
                    theta=theta, 
                    pg_all=pg, 
                    # load_all=load - ls.reshape((self.T, -1), 'C')
                    load_all = load - ls,
                    solar_all = solar - solarc if self.no_solar > 0 else None,
                    wind_all = wind - windc if self.no_wind > 0 else None
                    )
        
        # slack bus angle
        constraints = self._slack_constraints(constraints=constraints, theta=theta)

        # reserve requirement
        # todo: consider area
        for t in range(self.T):
            constraints += [
                np.sum(self.pgmax) >= cp.sum(pg[t]) + self.reserve[t]
            ]

        # constraints on the decision variables
        constraints = self._variable_constraints(
                                                constraints=constraints, 
                                                load=load, 
                                                ls=ls,
                                                solar = solar if self.no_solar > 0 else None,
                                                solarc = solarc if self.no_solar > 0 else None,
                                                wind = wind if self.no_wind > 0 else None,
                                                windc = windc if self.no_wind > 0 else None
                                                )
        
        # formulate the problem
        problem = cp.Problem(cp.Minimize(obj), constraints)
        
        # ramp constraints
        if self.T > 1:
            for t in range(1, self.T):
                constraints += [pg[t] - pg[t-1] <= self.ru,
                                pg[t] - pg[t-1] >= -self.rd]
            constraints += [pg[0] - self.pg_init <= self.ru,
                            pg[0] - self.pg_init >= -self.rd] # initial ramp limit

        return problem
    
    def ncuc_with_int(self):
        
        """network constrained unit commitment (ncuc) with integer variable"""
        
        load = cp.Parameter((self.T * self.no_load), name = 'load')              # load forecast (T, no_load)
        pg = cp.Variable((self.T * self.no_gen), name = 'pg')                    # generation (T, no_gen)
        ug = cp.Variable((self.T * self.no_gen), boolean = True, name = 'ug')    # commitment status (T, no_gen)
        theta = cp.Variable((self.T * self.no_bus), name = 'theta')              # phase angle (T, no_bus)
        ls = cp.Variable((self.T * self.no_load), name = 'ls')                   # load shed (T, no_load)
        
        # reshape
        load = load.reshape((self.T, -1), 'C')
        # pg = pg.reshape((self.T, -1), 'C')
        ug = ug.reshape((self.T, -1), 'C')
        theta = theta.reshape((self.T, -1), 'C')
        ls = ls.reshape((self.T, -1), 'C')
        
        if self.T > 1:
            # dont include the start up and shut down status for T = 1
            yg = cp.Variable((self.T * self.no_gen), boolean = True, name = 'yg')    # start-up status (T, no_gen)
            zg = cp.Variable((self.T * self.no_gen), boolean = True, name = 'zg')    # shut-down status (T, no_gen)
            yg = yg.reshape((self.T, -1), 'C')
            zg = zg.reshape((self.T, -1), 'C')
        
        if self.no_solar > 0:
            solar = cp.Parameter((self.T * self.no_solar), name = 'solar')             # solar forecast (T * no_solar)
            solarc = cp.Variable((self.T * self.no_solar), name = 'solarc')            # solar curtailment (T * no_solar)
            solar = solar.reshape((self.T, -1), 'C')
            solarc = solarc.reshape((self.T, -1), 'C')
        
        if self.no_wind > 0:
            wind = cp.Parameter((self.T * self.no_wind), name = 'wind')                # wind forecast (T * no_wind)
            windc = cp.Variable((self.T * self.no_wind), name = 'windc')               # wind curtailment (T * no_wind)
            wind = wind.reshape((self.T, -1), 'C')
            windc = windc.reshape((self.T, -1), 'C')
        
        # # ! the quadratic term ls should always be in vector form: why???
        # ls = cp.Variable((self.T * self.no_load), name = 'ls')   
        
        # objective function
        obj = 0
        
        obj += cp.scalar_product(self.first_order_coeff, pg)                   # generation cost
        obj += 0.5 * cp.quad_form(pg, self.second_order_coeff)                # quadratic cost
        
        pg = pg.reshape((self.T, -1), 'C') # reshape
        
        for t in range(self.T):
            obj += cp.scalar_product(self.cf, ug[t])              # generator fixed cost
            # obj += cp.scalar_product(self.cv, pg[t])              # generator varying cost
            # obj += 0.5 * cp.quad_form(pg[t], np.diag(self.cv2))   # quadratic cost
            
            if self.T > 1:
                obj += cp.scalar_product(self.csu, yg[t])             # start-up cost
                obj += cp.scalar_product(self.csd, zg[t])             # shut-down cost
            
            obj += cp.scalar_product(self.cls, ls[t])              # load shed cost
            
            if self.no_solar > 0:
                obj += cp.scalar_product(self.csc, solarc[t])      # solar curtailment cost
            if self.no_wind > 0:
                obj += cp.scalar_product(self.cwc, windc[t])       # wind curtailment cost
        
        # obj += cp.scalar_product(self.penalty, ls)           # load shed cost    
        # obj += 0.5 * cp.quad_form(ls, np.diag(self.penalty))
        
        # constraints
        constraints = []
        
        if self.T > 1:
            
            # constraint with initial condition involved
            # when T = 1, we dont have the ramp constraints and ramp up and down constraints
            # e.g. we dont have the variable yg and zg
            for t in range(1,self.T):
                # on-off
                constraints += [yg[t] - zg[t] == ug[t] - ug[t-1]]  # commitment status
                # ramp up
                constraints += [
                    pg[t] - pg[t-1] <= cp.multiply(self.ru, ug[t-1]) + cp.multiply(self.rsu, yg[t])
                ]
                # ramp down
                # ! ug[t]
                constraints += [
                    pg[t-1] - pg[t] <= cp.multiply(self.rd, ug[t]) + cp.multiply(self.rsd, zg[t])
                ]
            
            # initial condition
            constraints += [yg[0] - zg[0] == ug[0] - self.ug_init]      
            constraints += [
                pg[0] - self.pg_init <= cp.multiply(self.ru, self.ug_init) + cp.multiply(self.rsu, yg[0])
            ]
            constraints += [
                self.pg_init - pg[0] <= cp.multiply(self.rd, ug[0]) + cp.multiply(self.rsd, zg[0])
            ]
        
            # constraint without initial condition involved
            for t in range(self.T):
                # on-off
                constraints += [yg[t] + zg[t] <= 1]
        
        for t in range(self.T):
            # generation limit
            constraints += [pg[t] <= cp.multiply(self.pgmax, ug[t]), pg[t] >= cp.multiply(self.pgmin, ug[t])]
        
        constraints = self._flow_constraint(constraints=constraints, theta=theta)

        constraints = self._power_balance_constraint(
                    constraints=constraints, 
                    theta=theta, 
                    pg_all=pg, 
                    load_all=load - ls,
                    solar_all = solar - solarc if self.no_solar > 0 else None,
                    wind_all = wind - windc if self.no_wind > 0 else None
                    )
        
        constraints = self._slack_constraints(constraints=constraints, theta=theta)

        # reserve requirement: related to the on-off condition
        for t in range(self.T):
            constraints += [
                cp.sum(cp.multiply(self.pgmax, ug[t])) >= cp.sum(pg[t]) + self.reserve[t]
            ]

        # constraints about load shedding
        constraints = self._variable_constraints(constraints=constraints, 
                                                load=load, 
                                                ls=ls,
                                                solar = solar if self.no_solar > 0 else None,
                                                solarc = solarc if self.no_solar > 0 else None,
                                                wind = wind if self.no_wind > 0 else None,
                                                windc = windc if self.no_wind > 0 else None
                                                )
        
        # formulate the problem
        problem = cp.Problem(cp.Minimize(obj), constraints)
        
        return problem
    
    def ed(self, with_int):
        
        """formulate the economic dispatch problem (ed) with/out binary variable
        the integer here is a parameter passed from the ncuc stage results"""
        
        # parameters and variables
        if with_int:
            # ! remove boolean=True
            ug = cp.Parameter((self.T * self.no_gen), name = 'ug') # commitment status (no_gen)
            ug = ug.reshape((self.T, -1), 'C')
        else:
            ug = np.ones((self.T, self.no_gen))
        
        load = cp.Parameter((self.T * self.no_load), name = 'load')     # true load
        pg_uc = cp.Parameter((self.T * self.no_gen), name = 'pg_uc') 
        
        pg = cp.Variable((self.T * self.no_gen), name = 'pg')            # generation
        theta = cp.Variable((self.T * self.no_bus), name = 'theta')      # phase angle
        ls = cp.Variable((self.T * self.no_load), name = 'ls')           # load shed
        es = cp.Variable((self.T * self.no_gen), name = 'es')            # energy storage
        
        # reshape
        load = load.reshape((self.T, -1), 'C')
        pg_uc = pg_uc.reshape((self.T, -1), 'C')
        # pg = pg.reshape((self.T, -1), 'C')
        theta = theta.reshape((self.T, -1), 'C')
        ls = ls.reshape((self.T, -1), 'C')
        es = es.reshape((self.T, -1), 'C')
        
        if self.no_solar > 0:
            solar = cp.Parameter((self.T * self.no_solar), name = 'solar') # true solar
            solarc = cp.Variable((self.T * self.no_solar), name = 'solarc')
            solar = solar.reshape((self.T, -1), 'C')
            solarc = solarc.reshape((self.T, -1), 'C')
        if self.no_wind > 0:
            wind = cp.Parameter((self.T * self.no_wind), name = 'wind')
            windc = cp.Variable((self.T * self.no_wind), name = 'windc')
            wind = wind.reshape((self.T, -1), 'C')
            windc = windc.reshape((self.T, -1), 'C')
        
        # objective function
        obj = 0
        obj += cp.scalar_product(self.first_order_coeff, pg)                   # generation cost
        obj += 0.5 * cp.quad_form(pg, self.second_order_coeff)                # quadratic cost
        
        pg = pg.reshape((self.T, -1), 'C') # reshape
        
        for t in range(self.T):
            # obj += cp.scalar_product(self.cv, pg[t])              # first order cost
            # obj += 0.5 * cp.quad_form(pg[t], np.diag(self.cv2))   # second order cost
            
            obj += cp.scalar_product(self.cls, ls[t])              # load shed cost
            obj += cp.scalar_product(self.ces, es[t])              # energy storage cost
            if self.no_solar > 0:
                obj += cp.scalar_product(self.csc, solarc[t])
            if self.no_wind > 0:
                obj += cp.scalar_product(self.cwc, windc[t])

        # constraints
        constraints = []
        for t in range(self.T):
            # generation limit
            constraints += [pg[t] <= cp.multiply(self.pgmax, ug[t]), 
                            pg[t] >= cp.multiply(self.pgmin, ug[t])]

            # ramp limit
            constraints += [pg[t] - pg_uc[t] <= cp.multiply(self.ru, ug[t]), 
                            pg[t] - pg_uc[t] >= -cp.multiply(self.rd, ug[t])]
            
        # branch flow limit
        constraints = self._flow_constraint(constraints=constraints, theta=theta)
        
        # power balance
        constraints = self._power_balance_constraint(
                    constraints=constraints, 
                    theta=theta, 
                    pg_all=pg - es, 
                    load_all=load - ls,
                    solar_all = solar - solarc if self.no_solar > 0 else None,
                    wind_all = wind - windc if self.no_wind > 0 else None
                    )
        
        # slack bus angle
        constraints = self._slack_constraints(constraints=constraints, theta=theta)
        
        # variable constraints
        constraints = self._variable_constraints(constraints=constraints, 
                                                load=load, 
                                                ls=ls,
                                                pg = pg,
                                                es = es,
                                                solar = solar if self.no_solar > 0 else None,
                                                solarc = solarc if self.no_solar > 0 else None,
                                                wind = wind if self.no_wind > 0 else None,
                                                windc = windc if self.no_wind > 0 else None
                                                )
        
        # formulate the problem
        problem = cp.Problem(cp.Minimize(obj), constraints)
        
        return problem
    
    def get_pf(self, theta):

        # calculate the power flow
        # if theta.ndim == 1:
        #     return self.Bf @ theta + self.Pfshift
        # else:
        #     return theta @ self.Bf.T  + self.Pfshift.reshape(1, -1)
        
        return theta.reshape((self.T, -1)) @ self.Bf.T + self.Pfshift.reshape(1, -1)
    
    @staticmethod
    def solve(prob, parameters: dict, verbose: bool = False, solver: str = 'GUROBI', **solver_options):
        """
        assign parameter and solve the problem
        the keys of the parameters should be the same as the parameter names in the problem
        """
        for param in prob.parameters():
            try:
                param.value = parameters[param.name()]
            except:
                raise ValueError(f'Parameter name {param.name()} not found in the problem or the dimension is not correct.')
            
        prob.solve(solver = getattr(cp, solver.upper()), verbose = verbose,
                    **solver_options)
    
    @staticmethod  
    def get_sol(prob, T = None, reshaped = False):
        """
        clean the output into a dictionary
        """
        sol = {}
        for var in prob.variables():
            sol[var.name()] = var.value if not reshaped else var.value.reshape(T, -1)
        
        return sol