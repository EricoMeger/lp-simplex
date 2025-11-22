# tableau.py
EPS = 1e-9

class Tableau:
    def __init__(self, tableau_rows, col_types, var_names, base_vars, objective_type="Max"):
        self.tableau = [row[:] for row in tableau_rows]
        self.col_types = col_types[:]
        self.var_names = var_names[:]
        self.base_vars = base_vars[:]
        self.objective_type = objective_type

    @classmethod
    def from_phase1(cls, A, comps, b, orig_var_names=None, objective_type="Max"):
        m = len(A)
        n = len(A[0]) if m > 0 else 0
        tableau = [row[:] for row in A]
        col_types = ['orig'] * n
        var_names = orig_var_names[:] if orig_var_names else [f"x{j+1}" for j in range(n)]
        base_vars = [None]*m

        slack_count = 0
        artificial_count = 0

        for i, comp in enumerate(comps):
            if comp == "<=":
                for r in range(m):
                    tableau[r].append(1.0 if r == i else 0.0)
                col_types.append("slack")
                var_names.append(f"s{slack_count+1}")
                base_vars[i] = n + slack_count
                slack_count += 1

            elif comp == ">=":
                for r in range(m):
                    tableau[r].append(-1.0 if r == i else 0.0)
                col_types.append("surplus")
                var_names.append(f"e{slack_count+1}")
                slack_count += 1

                for r in range(m):
                    tableau[r].append(1.0 if r == i else 0.0)
                col_types.append("artificial")
                var_names.append(f"a{artificial_count+1}")
                base_vars[i] = n + slack_count
                artificial_count += 1
                slack_count += 1

            elif comp == "=":
                for r in range(m):
                    tableau[r].append(1.0 if r == i else 0.0)
                col_types.append("artificial")
                var_names.append(f"a{artificial_count+1}")
                base_vars[i] = n + slack_count
                artificial_count += 1
                slack_count += 1

        for i in range(m):
            tableau[i].append(b[i])

        total_cols = len(tableau[0])
        obj_row = [0.0]*total_cols
        for j,t in enumerate(col_types):
            if t == "artificial":
                obj_row[j] = -1.0
        tableau.append(obj_row)

        for i in range(m):
            bv = base_vars[i]
            if bv is not None and col_types[bv] == "artificial":
                tableau[-1] = [tableau[-1][j] + tableau[i][j] for j in range(total_cols)]

        return cls(tableau, col_types, var_names, base_vars, objective_type)

    def print_tableau(self, iteration=0):
        m = len(self.tableau)-1
        header = ["VB"] + self.var_names + ["b"]
        print(f"=== Iteracao: {iteration} ===")
        print("".join(f"{h:>10}" for h in header))

        for i in range(m):
            bv = self.base_vars[i]
            vb = self.var_names[bv] if bv is not None else "?"
            print(f"{vb:>10}", end="")
            for v in self.tableau[i]:
                print(f"{v:>10.4f}", end="")
            print()

        print(f"{'OBJ':>10}", end="")
        for v in self.tableau[-1]:
            print(f"{v:>10.4f}", end="")
        print("\n")

    def find_pivot(self):
        last = self.tableau[-1]
        min_val = min(last[:-1])
        if min_val >= -EPS:
            return None
        pivot_col = last[:-1].index(min_val)

        ratios = []
        for i in range(len(self.tableau)-1):
            a = self.tableau[i][pivot_col]
            if a > EPS:
                ratios.append((self.tableau[i][-1]/a, i))

        if not ratios:
            return ("unbounded", pivot_col)

        ratios.sort(key=lambda x: (x[0], x[1]))
        return ratios[0][1], pivot_col

    def pivot(self, r, c):
        pv = self.tableau[r][c]
        self.tableau[r] = [v / pv for v in self.tableau[r]]

        for i in range(len(self.tableau)):
            if i == r:
                continue
            f = self.tableau[i][c]
            self.tableau[i] = [
                self.tableau[i][j] - f*self.tableau[r][j] for j in range(len(self.tableau[0]))
            ]

        self.base_vars[r] = c

    def run_simplex(self, verbose=True, max_iter=500):
        it = 0
        while True:
            it += 1

            # Só imprime quando a linha OBJ já existe e tem o tamanho correto
            if verbose and len(self.tableau[-1]) == len(self.tableau[0]):
                self.print_tableau(iteration=it)

            pv = self.find_pivot()
            if pv is None:
                return "optimal"
            if pv[0] == "unbounded":
                return "unbounded"

            r, c = pv
            self.pivot(r, c)

            if it >= max_iter:
                return "max_iter"

    def remove_artificials(self):
        cols_to_remove = [i for i,t in enumerate(self.col_types) if t == "artificial"]

        remap = {}
        jnew = 0
        for j in range(len(self.col_types)):
            if j not in cols_to_remove:
                remap[j] = jnew
                jnew += 1

        new_col_types = [t for i,t in enumerate(self.col_types) if i not in cols_to_remove]
        new_var_names  = [v for i,v in enumerate(self.var_names) if i not in cols_to_remove]

        new_tableau = []
        for i in range(len(self.tableau)-1):
            new_tableau.append([
                val for j,val in enumerate(self.tableau[i]) if j not in cols_to_remove
            ])

        new_base = []
        for bv in self.base_vars:
            if bv in remap:
                new_base.append(remap[bv])
            else:
                new_base.append(None)

        return Tableau(new_tableau, new_col_types, new_var_names, new_base, self.objective_type)

    def set_objective_from_original(self, c_orig, objective_type="Max"):
        total_cols = len(self.tableau[0])
        obj = [0.0]*total_cols

        orig_idx = [i for i,t in enumerate(self.col_types) if t == "orig"]
        for k,j in enumerate(orig_idx):
            if k < len(c_orig):
                obj[j] = -c_orig[k] if objective_type=="Max" else c_orig[k]

        obj[-1] = 0.0

        for i in range(len(self.tableau)-1):
            bv = self.base_vars[i]
            if bv is not None and abs(obj[bv]) > EPS:
                f = obj[bv]
                obj = [obj[j]-f*self.tableau[i][j] for j in range(len(obj))]

        self.tableau.append(obj)

    def extract_solution_expanded(self, k):
        m = len(self.tableau)-1
        sol = [0.0]*k

        for col in range(k):
            row = None
            ok = True

            for i in range(m):
                if abs(self.tableau[i][col]-1) < EPS:
                    if row is not None:
                        ok = False
                        break
                    row = i
                elif abs(self.tableau[i][col]) > EPS:
                    ok = False
                    break

            sol[col] = self.tableau[row][-1] if ok and row is not None else 0.0

        return sol
