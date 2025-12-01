from tableau import Tableau
import os

class Simplex:
    def __init__(self, objective_coeffs, constraints, 
                 objective_type="Max", var_signs=None):
        """
        Args:
            objective_coeffs: objective function coefficients 
            constraints: List of tuples (coefficients, operator, rhs)
            objective_type: "Max" (only maximization is supported)
            non_negative: List indicating if each variable is non-negative
        """
        self.original_objective_type = objective_type
        self.orig_num_vars = len(objective_coeffs)
        self.var_signs = var_signs if var_signs else [">=0"] * self.orig_num_vars
        self.original_constraints = constraints[:]

        self.c, self.constraints, self._map_orig_to_internal = self.expand_variables(
            objective_coeffs, constraints, self.var_signs
        )

        if objective_type == "Min":
            self.c = [-float(x) for x in self.c]
            self.is_minimization = True
        else:
            self.c = [float(x) for x in self.c]
            self.is_minimization = False
        
        self.objective_type = "Max"
        self.num_vars = len(self.c)
        self.M = 1000000
        self.tableau_obj = None
        self.artificial_indices = []
        self.solution = None
        self.optimal_value = None
        self.iteration_logs = []

    def expand_variables(self, c, constraints, var_signs):
        n = len(c)
        A = [list(coeffs) for (coeffs, _, _) in constraints]
        ops = [op for (_, op, _) in constraints]
        b = [rhs for (_, _, rhs) in constraints]

        new_c = []
        mapping = []
        col_blocks = []
        for i in range(n):
            sign = var_signs[i] if i < len(var_signs) else ">=0"
            if sign == ">=0":
                mapping.append([len(new_c)])
                new_c.append(float(c[i]))
                col_blocks.append(("single", i, [len(new_c)-1]))
            elif sign == "<=0":
                mapping.append([len(new_c)])
                new_c.append(float(-c[i]))
                col_blocks.append(("neg", i, [len(new_c)-1]))
            else:
                mapping.append([len(new_c), len(new_c)+1])
                new_c.append(float(c[i]))
                new_c.append(float(-c[i]))
                col_blocks.append(("free", i, [len(new_c)-2, len(new_c)-1]))

        A_exp = []
        for r in range(len(constraints)):
            row = [0.0] * len(new_c)
            for i in range(n):
                a = float(A[r][i])
                typ, _, idxs = col_blocks[i]
                if typ == "single":
                    row[idxs[0]] = a
                elif typ == "neg":
                    row[idxs[0]] = -a
                else:
                    row[idxs[0]] = a
                    row[idxs[1]] = -a
            A_exp.append(row)

        constraints_exp = [(A_exp[i], ops[i], b[i]) for i in range(len(constraints))]
        return new_c, constraints_exp, mapping
        
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

        self.iteration_logs.append(self.tableau_obj.format_tableau(iteration=0))
        self.tableau_obj.print_tableau(iteration=0)
        
        while iteration < max_iterations:
            iteration += 1
            
            pivot_col = self.find_pivot_column()
            if pivot_col is None:
                if self.check_artificial_in_basis():
                    return "infeasible"
                return "optimal"
            
            pivot_row = self.find_pivot_row(pivot_col)
            if pivot_row is None:
                return "unbounded"
            
            self.pivot(pivot_row, pivot_col)
            all_var_names = self.tableau_obj.get_all_var_names()
            self.tableau_obj.basis[pivot_row] = all_var_names[pivot_col]

            self.iteration_logs.append(self.tableau_obj.format_tableau(iteration=iteration))
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
        internal_solution = [0.0] * self.num_vars
        all_var_names = self.tableau_obj.get_all_var_names()
        for i, var_name in enumerate(self.tableau_obj.basis):
            if var_name and var_name.startswith('x'):
                var_index = int(var_name[1:]) - 1
                internal_solution[var_index] = self.tableau_obj.tableau[i][-1]

        sol = [0.0] * self.orig_num_vars
        for i, idxs in enumerate(self._map_orig_to_internal):
            if len(idxs) == 1:
                if self.var_signs[i] == "<=0":
                    sol[i] = -internal_solution[idxs[0]]
                else:
                    sol[i] = internal_solution[idxs[0]]
            else:
                plus, minus = idxs
                sol[i] = internal_solution[plus] - internal_solution[minus]

        self.solution = sol
        self.optimal_value = self.tableau_obj.tableau[-1][-1]
        if self.is_minimization:
            self.optimal_value = -self.optimal_value

    def write_report(self, filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        lines = []

        lines.append("Iterações do Simplex")
        lines.append("=" * 80)
        lines.extend(self.iteration_logs)
        lines.append("=" * 80)
        lines.append("Solução")
        lines.append("")
        lines.append(f"FO: {self.optimal_value:.4f}")
        
        for i, v in enumerate(self.solution, start=1):
            lines.append(f"x{i} = {v:.4f}")
        lines.append("")
        
        for k, (coeffs, op, rhs) in enumerate(self.original_constraints, start=1):
            lhs = 0.0
            for j, a in enumerate(coeffs):
                lhs += float(a) * float(self.solution[j] if j < len(self.solution) else 0.0)
            if op == "<=":
                line = f"R{k} = None <= {lhs:.4f} <= {float(rhs):.4f}"
            elif op == ">=":
                line = f"R{k} = {float(rhs):.4f} <= {lhs:.4f} <= None"
            else:
                line = f"R{k} = {float(rhs):.4f} <= {lhs:.4f} <= {float(rhs):.4f}"
            lines.append(line)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")