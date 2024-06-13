"""
return the standard form of the operation problem as QP or LP
"""

import cvxpy as cp
from cvxpy.reductions.solvers.conic_solvers.scs_conif import dims_to_solver_dict

def return_compiler(prob):

    data, _, _ = prob.get_problem_data(
                solver=cp.GUROBI, solver_opts={'use_quad_obj': True})  # set True can force the objective to be quadrtic
    
    assert data['dims'].exp == 0, 'does not support cone'
    assert len(data['dims'].psd) == 0, 'does not support cone'
    assert len(data['dims'].soc) == 0, 'does not support cone'

    compiler = data[cp.settings.PARAM_PROB]
    params_idx = {p.id: p.name() for p in prob.parameters()}  # the order of parameter ids are changed internally

    return compiler, params_idx, data['dims'].zero, data['int_vars_idx'], data['bool_vars_idx']

def return_standard_form(compiler, params_val: dict, zero_dim: int):
    """find the compiler first to save time
    the order of params_val should be the same as the param_ids
    output[0]: P (with 1/2 being considered)
    output[1]: q
    output[2]: r
    output[3]: [eq_matrix; ineq_matrix]
    output[4]: [eq_vec; ineq_vec]"""
    
    output = compiler.apply_parameters(
                    params_val,
                    keep_zeros=True)
    
    P = output[0].toarray()
    q = output[1]
    r = output[2]
    A = output[3].toarray()[:zero_dim]
    b = -output[4][:zero_dim]
    G = -output[3].toarray()[zero_dim:]
    h = output[4][zero_dim:]
    
    return P, q, r, A, b, G, h