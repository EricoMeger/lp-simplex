# tableau.py
EPS = 1e-9

class Tableau:
    def __init__(self, A, b, c):
        """
        A = constraints matrix (lista de listas com coeficientes)
        b = independent terms (lista com RHS das restrições)
        c = coefficients of the objective function (lista)
        """
        self.A = A
        self.b = b
        self.c = c

        self.num_constraints = len(A)
        self.num_vars = len(c)

        self.var_names = [f"x{i+1}" for i in range(self.num_vars)]
        
        self.slack_vars = []
        self.artificial_vars = []
        
        self.basis = []
        
        self.tableau = []

    def add_slack_variable(self, name=None):
        if name is None:
            name = f"w{len(self.slack_vars) + 1}"
        self.slack_vars.append(name)
        return name

    def add_artificial_variable(self, name=None):
        if name is None:
            name = f"a{len(self.artificial_vars) + 1}"
        self.artificial_vars.append(name)
        return name

    def build_tableau(self, slack_indices, artificial_indices=None, M=1000000, slack_types=None):
        """
        Constrói o tableau do simplex.
        
        Args:
            slack_indices: index list of constraints that receive slack variables
            artificial_indices: index list of constraints that receive artificial variables
            M: Big M penalty value for artificial variables
            slack_types: dictionary {constraint_index: coef} where coef is 1 (<=) or -1 (>=)
        """
        m = self.num_constraints
        n = self.num_vars
        num_slack = len(slack_indices) if slack_indices else 0
        num_artificial = len(artificial_indices) if artificial_indices else 0
        num_cols = n + num_slack + num_artificial + 1
        self.tableau = [[0.0] * num_cols for _ in range(m + 1)]

        for i in range(m):
            for j in range(n):
                self.tableau[i][j] = float(self.A[i][j])
            self.tableau[i][-1] = float(self.b[i])

        base = [None] * m

        slack_col = n
        for idx in (slack_indices or []):
            var_name = self.add_slack_variable()
            coef = 1.0 if slack_types is None else slack_types.get(idx, 1.0)
            self.tableau[idx][slack_col] = coef
            if coef == 1.0:
                base[idx] = var_name
            slack_col += 1

        artificial_col = n + num_slack
        artificial_col_indices = []
        for idx in (artificial_indices or []):
            var_name = self.add_artificial_variable()
            self.tableau[idx][artificial_col] = 1.0
            base[idx] = var_name
            artificial_col_indices.append(artificial_col)
            artificial_col += 1

        for j in range(n):
            self.tableau[-1][j] = -float(self.c[j])

        for col_idx in artificial_col_indices:
            self.tableau[-1][col_idx] = M
        if artificial_indices:
            for idx in artificial_indices:
                for j in range(num_cols):
                    self.tableau[-1][j] -= M * self.tableau[idx][j]

        self.basis = base

    def get_all_var_names(self):
        return self.var_names + self.slack_vars + self.artificial_vars

    # ==========================================================
    # Impressão do tableau
    # ==========================================================
    def print_tableau(self, iteration=0):
        all_vars = self.get_all_var_names()
        cabecalho = ["VB"] + all_vars + ["b"]
        largura = 8

        print(f"=== Iteracao: {iteration} ===")
        print(f"{cabecalho[0]:>15}", end="")
        for elemento in cabecalho[1:]:
            print(f"{elemento:>{largura}}", end="")
        print()

        for i, var in enumerate(self.basis):
            print(f"{var:>15}", end="")
            for valor in self.tableau[i]:
                print(f"{valor:>{largura}.2f}", end="")
            print()

        print(f"{'Z':>15}", end="")  
        for valor in self.tableau[-1]:
            print(f"{valor:>{largura}.2f}", end="")
        print()