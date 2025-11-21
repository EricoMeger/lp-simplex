class Tableau:
    def __init__(self, A, b, c, objective_type):
        """
        A = constraints matrix
        b = independent terms
        c = coefficients of the objective function
        objective_type = "Max" or "Min"
        """

        self.A = A
        self.b = b
        self.c = c
        self.objective_type = objective_type

        self.num_constraints = len(A)
        self.num_vars = len(c)

        self.var_names = [f"x{i+1}" for i in range(self.num_vars)]

        self.base_vars = [f"w{i+1}" for i in range(self.num_constraints)]

        self.build_tableau()

    def build_tableau(self):
        n = self.num_vars
        m = self.num_constraints

        self.tableau = []
        for i in range(m):
            row = self.A[i] + [0] * m + [self.b[i]]
            row[n + i] = 1 
            self.tableau.append(row)

        if self.objective_type == "Max":
            obj = [-ci for ci in self.c] 
        else:  # Min
            obj = self.c[:] 

        obj = obj + [0] * m + [0] 
        self.tableau.append(obj)

    def print_tableau(self, iteration=0):
        Cabecalho = ["VB", "-Z"] + self.var_names + self.base_vars + ["b"]
        largura = 6 

        print(f"=== Iteracao: {iteration} ===")
        print(f"{Cabecalho[0]:>15}", end="")
        for elemento in Cabecalho[1:]:
            print(f"{elemento:>{largura}}", end="")
        print()

        for i, var in enumerate(self.base_vars):
            print(f"{var:>15}", end="")
            for valor in self.tableau[i]:
                print(f"{valor:>{largura}.2f}", end="")
            print()

        print(f"{'-Z':>15}", end="")
        for valor in self.tableau[-1]:
            print(f"{valor:>{largura}.2f}", end="")
        print()
        print()
