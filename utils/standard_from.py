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

def return_standard_form(prob, params_val_dict):
    """find the compiler first to save time
    prob: a cvxpy problem
    the order of params_val should be the same as the param_ids
    output[0]: P (with 1/2 being considered)
    output[1]: q
    output[2]: r
    output[3]: [eq_matrix; ineq_matrix]
    output[4]: [eq_vec; ineq_vec]"""

    param_qp_prog, params_idx, zero_dim, int_dim, bool_dim = return_compiler(prob)
    params_val = {idx: params_val_dict[name] for idx, name in params_idx.items()}
    
    output = param_qp_prog.apply_parameters(
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

def return_bool_idx(prob):
    """
    return the index of the boolean variables
    prob: a cvxpy problem
    """
    data, _, _ = prob.get_problem_data(
                solver=cp.GUROBI, solver_opts={'use_quad_obj': True})  
    
    return data['bool_vars_idx']

def return_standard_form_no_value(prob, as_tensor = False):
    """
    standard form of the QP problem without parameter value
    idx_to_name: {param_id: param_name}, link the id to the parameter name
    """

    param_id_to_name = {p.id: p.name() for p in prob.parameters()}  # the idx to name dictionary
    param_qp_prog, params_idx, zero_dim, int_dim, bool_dim = return_compiler(prob)

    no_cons = param_qp_prog.constr_size
    no_var = param_qp_prog.reduced_A.var_len

    P = param_qp_prog.P.toarray()[:,-1].reshape(no_var, no_var)
    q = param_qp_prog.q.toarray()[:-1,-1]

    A_tilde = param_qp_prog.A.toarray()[:int(no_cons * no_var), -1]
    A_tilde = A_tilde.reshape(no_var, no_cons).T

    b_tilde = param_qp_prog.A.toarray()[int(no_cons * no_var):, -1]

    A = A_tilde[:zero_dim,:]
    G = -A_tilde[zero_dim:,:]

    b = -b_tilde[:zero_dim]
    h = b_tilde[zero_dim:]

    B_tilde = param_qp_prog.A.toarray()[int(no_cons * no_var):, :-1]

    # ! support multiple parameters
    B = {}
    H = {}

    param_id_to_col = param_qp_prog.param_id_to_col
    param_id_to_size = param_qp_prog.param_id_to_size

    for key, start_idx in param_id_to_col.items():
        if key == -1:
            break
        size = param_id_to_size[key]
        name = param_id_to_name[key]
        B[name] = -B_tilde[:zero_dim, start_idx:start_idx+size]
        H[name] = B_tilde[zero_dim:, start_idx:start_idx+size] 
    
    # find the matrix corresponding to the parameter in b
    # # ! only support single parameter
    # B = -B_tilde[:zero_dim, :]
    # H = B_tilde[zero_dim:, :]
        
    # if as_tensor:
    #     P = torch.tensor(P)
    #     q = torch.tensor(q)
    #     A = torch.tensor(A)
    #     G = torch.tensor(G)
    #     b = torch.tensor(b)
    #     h = torch.tensor(h)
    #     for key in B.keys():
    #         B[key] = torch.tensor(B[key])
    #         H[key] = torch.tensor(H[key])

    return P, q, A, G, b, h, B, H # NOTE: negative sign

def return_standard_form_in_cvxpy(prob):
    """
    return the standard form of the problem fommated as cvxpy
    standard form
    min 1/2 x^T P x + q^T x
    s.t. A x = b + \sum B_i z_i
         G x <= h + \sum H_i z_i
    in which x is the decision variable, z_i is the i-th parameter
    """
    
    P, q, A, G, b, h, B, H = return_standard_form_no_value(prob)
    bool_idx = return_bool_idx(prob)
    
    x = cp.Variable(P.shape[1])
    parameters = {
        key: 
        cp.Parameter(B[key].shape[1], name = key) for key in B.keys()
        } # paramters for the standard QP
    
    # formulate the cvxpy problem
    objective = cp.Minimize(0.5 * cp.quad_form(x, P) + q @ x)
    constraints = []
    if len(bool_idx) > 0:
        # set the integer (binary) constraints
        constraints += [cp.FiniteSet(x[bool_idx], [0, 1])]
    
    b_ = 0
    h_ = 0
    
    for key in B.keys():
        b_ += B[key] @ parameters[key]
        h_ += H[key] @ parameters[key]
    
    constraints += [A @ x == b_ + b, G @ x <= h_ + h]
    
    prob = cp.Problem(objective, constraints)
    
    return prob