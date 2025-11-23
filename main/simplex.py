from tableau import Tableau

class Simplex:
    def __init__(self, objective_coeffs, constraints, 
                 objective_type="Max", non_negative=None):
        """
        Args:
            objective_coeffs: objective function coefficients 
            constraints: List of tuples (coefficients, operator, rhs)
            objective_type: "Max" (only maximization is supported)
            non_negative: List indicating if each variable is non-negative
        """
        if objective_type != "Max":
            raise ValueError("Only maximization is supported.")
        
        self.c = [float(x) for x in objective_coeffs]
        self.constraints = constraints
        self.objective_type = objective_type
        self.num_vars = len(objective_coeffs)
        self.non_negative = non_negative if non_negative else [True] * self.num_vars
        
        self.M = 1000000
        
        self.tableau_obj = None
        
        self.artificial_indices = []
        
        self.solution = None
        self.optimal_value = None
        
    def solve(self):
        """
        Solves the LP problem using the Simplex method with Big M.
        
        Returns:
            dict with 'status', 'solution', 'optimal_value'
        """
        self.prepare_tableau()
        
        status = self.simplex_iterations()
        
        if status == "optimal":
            self.extract_solution()
            
        return {
            "status": status,
            "solution": self.solution,
            "optimal_value": self.optimal_value
        }
    
    def prepare_tableau(self):
        """
        Prepares the initial tableau:
        - Processes constraints
        - Identifies which need slack/artificial variables
        - Creates the tableau using the Tableau class
        """
        A = []  
        b = []  
        slack_indices = []
        artificial_indices = []
        slack_types = {} 
        
        for i, (coeffs, op, rhs) in enumerate(self.constraints):
            coeffs = [float(x) for x in coeffs]
            rhs = float(rhs)
            
            # if RHS is negative we multiply by -1 and invert the operator
            if rhs < 0:
                coeffs = [-x for x in coeffs]
                rhs = -rhs
                if op == "<=":
                    op = ">="
                elif op == ">=":
                    op = "<="
            
            A.append(coeffs)
            b.append(rhs)
            
            if op == "<=":
                # add a slack variable with coefficient +1
                slack_indices.append(i)
                slack_types[i] = 1.0
                
            elif op == ">=":
                # add a slack variable with coefficient -1 and a artificial variable
                slack_indices.append(i)
                slack_types[i] = -1.0
                artificial_indices.append(i)
                
            else:  # op == "="
                # add only an artificial variable
                artificial_indices.append(i)
        
        self.tableau_obj = Tableau(A, b, self.c)
        self.tableau_obj.build_tableau(
            slack_indices=slack_indices,
            artificial_indices=artificial_indices,
            M=self.M,
            slack_types=slack_types
        )
        
        num_slack = len(slack_indices)
        for i, idx in enumerate(artificial_indices):
            col_idx = self.num_vars + num_slack + i
            self.artificial_indices.append(col_idx)
    
    def simplex_iterations(self):
        """
        Returns:
            "optimal", "unbounded" or "infeasible"
        """
        max_iterations = 1000
        iteration = 0
        
        self.tableau_obj.print_tableau(iteration=0)
        
        while iteration < max_iterations:
            iteration += 1
            
            pivot_col = self.find_pivot_column()
            
            if pivot_col is None:
                if self.check_artificial_in_basis():
                    return "infeasible"
                return "optimal"
            
            # find pivot row (variable leaving the basis)
            pivot_row = self.find_pivot_row(pivot_col)
            
            if pivot_row is None:
                return "unbounded"
            
            self.pivot(pivot_row, pivot_col)
            
            all_var_names = self.tableau_obj.get_all_var_names()
            self.tableau_obj.basis[pivot_row] = all_var_names[pivot_col]
            
            self.tableau_obj.print_tableau(iteration=iteration)
        
        return "max_iterations_reached"
    
    def find_pivot_column(self):
        """
        Find the pivot column (non-basic variable with most negative coefficient).
        Uses Bland's rule to avoid cycling.
        
        Returns:
            Index of the pivot column or None if optimal
        """
        obj_row = self.tableau_obj.tableau[-1][:-1]
        
        min_val = min(obj_row)
        
        if min_val >= -1e-10:  
            return None
        
        for i, val in enumerate(obj_row):
            if abs(val - min_val) < 1e-10:
                return i
        
        return None
    
    def find_pivot_row(self, pivot_col):
        m = len(self.tableau_obj.basis)
        ratios = []
        
        for i in range(m):
            if self.tableau_obj.tableau[i][pivot_col] > 1e-10:
                ratio = self.tableau_obj.tableau[i][-1] / self.tableau_obj.tableau[i][pivot_col]
                ratios.append((ratio, i))
            else:
                ratios.append((float('inf'), i))
        
        valid_ratios = [(r, i) for r, i in ratios if r >= 0]
        
        if not valid_ratios:
            return None  # means that the problem is unbounded
        
        min_ratio = min(r for r, _ in valid_ratios)
        
        for r, i in valid_ratios:
            if abs(r - min_ratio) < 1e-10:
                return i
        
        return None
    
    def pivot(self, pivot_row, pivot_col):
        pivot = self.tableau_obj.tableau[pivot_row][pivot_col]
        num_cols = len(self.tableau_obj.tableau[0])
        
        for j in range(num_cols):
            self.tableau_obj.tableau[pivot_row][j] /= pivot
        
        for i in range(len(self.tableau_obj.tableau)):
            if i != pivot_row:
                multiplier = self.tableau_obj.tableau[i][pivot_col]
                for j in range(num_cols):
                    self.tableau_obj.tableau[i][j] -= multiplier * self.tableau_obj.tableau[pivot_row][j]
    
    def check_artificial_in_basis(self):
        """
        Check for artificial variables in the basis with positive value.
        If true, the problem is infeasible.
        """
        all_var_names = self.tableau_obj.get_all_var_names()
        
        for i, var_name in enumerate(self.tableau_obj.basis):
            if var_name.startswith('a'):
                if self.tableau_obj.tableau[i][-1] > 1e-10:
                    return True
        return False
    
    def extract_solution(self):
        self.solution = [0.0] * self.num_vars
        
        all_var_names = self.tableau_obj.get_all_var_names()
        
        for i, var_name in enumerate(self.tableau_obj.basis):
            if var_name and var_name.startswith('x'):
                var_index = int(var_name[1:]) - 1
                self.solution[var_index] = self.tableau_obj.tableau[i][-1]
        
        self.optimal_value = self.tableau_obj.tableau[-1][-1]