"""
return the standard form of the operation problem as QP or LP
"""

import cvxpy as cp
from cvxpy.reductions.solvers.conic_solvers.scs_conif import dims_to_solver_dict

def return_compiler(prob):
    """
    return the compiler of the problem given by cvxpy
    return:
        - compiler: the compiler of the problem in standard form
        - params_idx: {param_id: param_name}, link the id to the parameter name
        - zero_dim: the number of equality constraint in the standard form 
                                        (always be the first rows in the matrix)
        - int_vars_idx: the index of integer variables
        - bool_vars_idx: the index of boolean variables
    """

    data, _, _ = prob.get_problem_data(
                solver=cp.GUROBI, solver_opts={'use_quad_obj': True})  
    # ! set True can force the objective to be quadrtic

    assert data['dims'].exp == 0, 'does not support cone'
    assert len(data['dims'].psd) == 0, 'does not support cone'
    assert len(data['dims'].soc) == 0, 'does not support cone'

    # parametric QP problem
    param_qp_prog = data[cp.settings.PARAM_PROB]
    
    # ! the order of parameter idx is changed internally in cvxpy so we link the id to the name
    params_idx = {p.id: p.name() for p in prob.parameters()}  

    return param_qp_prog, params_idx, data['dims'].zero, data['int_vars_idx'], data['bool_vars_idx']

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


def return_standard_form_no_value(param_qp_prog, zero_dims):
    """
    standard form of the QP problem without parameter value
    """
    no_cons = param_qp_prog.constr_size
    no_var = param_qp_prog.reduced_A.var_len

    P = param_qp_prog.P.toarray()[:,-1].reshape(no_var, no_var)
    q = param_qp_prog.q.toarray()[:-1,-1]

    A_tilde = param_qp_prog.A.toarray()[:int(no_cons * no_var), -1]
    A_tilde = A_tilde.reshape(no_var, no_cons).T

    b_tilde = param_qp_prog.A.toarray()[int(no_cons * no_var):, -1]

    A = A_tilde[:zero_dims,:]
    G = -A_tilde[zero_dims:,:]

    b = -b_tilde[:zero_dims]
    h = b_tilde[zero_dims:]

    B_tilde = param_qp_prog.A.toarray()[int(no_cons * no_var):, :-1]

    B = {}
    H = {}

    param_id_to_col = param_qp_prog.param_id_to_col
    param_id_to_size = param_qp_prog.param_id_to_size

    for key, start_idx in param_id_to_col.items():
        if key == -1:
            break
        size = param_id_to_size[key]
        B[key] = -B_tilde[:zero_dims, start_idx:start_idx+size]
        H[key] = B_tilde[zero_dims:, start_idx:start_idx+size] 
    
    # # find the matrix corresponding to the parameter in b
    # # ! only support single parameter
    # B = B_tilde[:zero_dims, :]
    # H = B_tilde[zero_dims:, :]

    return P, q, A, G, b, h, B, H # NOTE: negative sign