# tableau.py
EPS = 1e-9

class Tableau:
    def __init__(self, tableau_rows, col_types, var_names, base_vars, objective_type="Max"):
        self.tableau = [row[:] for row in tableau_rows]
        self.col_types = col_types[:]        # orig, slack, surplus, artificial
        self.var_names = var_names[:]        # nomes das colunas
        self.base_vars = base_vars[:]        # índice da coluna básica por linha
        self.objective_type = objective_type

    # ==========================================================
    # FASE 1 - Construção do tableau
    # ==========================================================
    @classmethod
    def from_phase1(cls, A, comps, b, orig_var_names=None, objective_type="Max"):
        m = len(A)
        n = len(A[0]) if m > 0 else 0

        tableau = [row[:] for row in A]

        col_types = ['orig'] * n
        var_names = orig_var_names[:] if orig_var_names else [f"x{j+1}" for j in range(n)]
        base_vars = [None] * m

        slack_count = 0
        artificial_count = 0

        for i, comp in enumerate(comps):

            # <=  ---> + slack
            if comp == "<=":
                col = len(col_types)
                for r in range(m):
                    tableau[r].append(1.0 if r == i else 0.0)

                col_types.append("slack")
                var_names.append(f"s{slack_count+1}")
                base_vars[i] = col
                slack_count += 1

            # >= ---> surplus (-1) + artificial (+1)
            elif comp == ">=":
                # Surplus
                col_surp = len(col_types)
                for r in range(m):
                    tableau[r].append(-1.0 if r == i else 0.0)

                col_types.append("surplus")
                var_names.append(f"e{slack_count+1}")
                slack_count += 1

                # Artificial
                col_art = len(col_types)
                for r in range(m):
                    tableau[r].append(1.0 if r == i else 0.0)

                col_types.append("artificial")
                var_names.append(f"a{artificial_count+1}")
                base_vars[i] = col_art
                artificial_count += 1

            # = ---> + artificial
            elif comp == "=":
                col_art = len(col_types)
                for r in range(m):
                    tableau[r].append(1.0 if r == i else 0.0)

                col_types.append("artificial")
                var_names.append(f"a{artificial_count+1}")
                base_vars[i] = col_art
                artificial_count += 1

        # coluna b
        for i in range(m):
            tableau[i].append(b[i])

        # ==========================================================
        # Linha OBJ da fase 1: minimizar soma das artificiais → coef −1
        # ==========================================================
        total_cols = len(tableau[0])
        obj_row = [0.0] * total_cols

        for j, t in enumerate(col_types):
            if t == "artificial":
                obj_row[j] = -1.0

        # adiciona linha obj
        tableau.append(obj_row)

        # corrige linha OBJ adicionando linhas com artificiais básicas
        for i in range(m):
            bv = base_vars[i]
            if bv is not None and col_types[bv] == "artificial":
                tableau[-1] = [
                    tableau[-1][j] + tableau[i][j]
                    for j in range(total_cols)
                ]

        return cls(tableau, col_types, var_names, base_vars, objective_type)

    # ==========================================================
    # Impressão do tableau
    # ==========================================================
    def print_tableau(self, iteration=0):
        m = len(self.tableau) - 1
        header = ["VB"] + self.var_names + ["b"]

        print(f"=== Iteracao: {iteration} ===")
        print("".join(f"{h:>10}" for h in header))

        for i in range(m):
            bv = self.base_vars[i]
            vb_name = self.var_names[bv] if bv is not None else "?"
            print(f"{vb_name:>10}", end="")
            for v in self.tableau[i]:
                print(f"{v:>10.4f}", end="")
            print()

        print(f"{'OBJ':>10}", end="")
        for v in self.tableau[-1]:
            print(f"{v:>10.4f}", end="")
        print("\n")

    # ==========================================================
    # Simplex pivot (FASE 1 e FASE 2)
    # ==========================================================
    def find_pivot(self):
        last = self.tableau[-1]
        # Detect Phase 1 (artificials still present). In Phase 1 we are
        # maximizing -w (row built as negative of the sum of artificials).
        # So entering column should have POSITIVE coefficient.
        phase1 = any(t == "artificial" for t in self.col_types)

        if phase1:
            # Choose column with largest positive coefficient
            candidates = [(val, j) for j, val in enumerate(last[:-1]) if val > EPS]
            if not candidates:
                return None  # Optimal for Phase 1 (all artificials driven to zero)
            # pick with max positive value
            _, pivot_col = max(candidates, key=lambda x: x[0])
        else:
            # Phase 2 (standard maximization with negative costs in row)
            candidates = [(val, j) for j, val in enumerate(last[:-1]) if val < -EPS]
            if not candidates:
                return None  # Optimal for Phase 2
            # pick most negative
            _, pivot_col = min(candidates, key=lambda x: x[0])

        # Ratio test (same for both phases): need a_ij > 0
        ratios = []
        for i in range(len(self.tableau) - 1):
            a = self.tableau[i][pivot_col]
            if a > EPS:
                ratios.append((self.tableau[i][-1] / a, i))

        if not ratios:
            return ("unbounded", pivot_col)

        ratios.sort()
        return ratios[0][1], pivot_col

    def pivot(self, r, c):
        pv = self.tableau[r][c]
        self.tableau[r] = [v / pv for v in self.tableau[r]]

        for i in range(len(self.tableau)):
            if i != r:
                f = self.tableau[i][c]
                self.tableau[i] = [
                    self.tableau[i][j] - f * self.tableau[r][j]
                    for j in range(len(self.tableau[0]))
                ]

        self.base_vars[r] = c

    # ==========================================================
    # Loop do simplex
    # ==========================================================
    def run_simplex(self, verbose=True, max_iter=200):
        it = 0
        while True:
            it += 1
            if verbose:
                self.print_tableau(it)

            pv = self.find_pivot()
            if pv is None:
                return "optimal"
            if pv[0] == "unbounded":
                return "unbounded"

            r, c = pv
            self.pivot(r, c)

            if it >= max_iter:
                return "max_iter"

    # ==========================================================
    # Remover artificiais para Fase 2
    # ==========================================================
    def remove_artificials(self):
        cols_to_remove = [i for i, t in enumerate(self.col_types) if t == "artificial"]

        remap = {}
        jnew = 0
        for j in range(len(self.col_types)):
            if j not in cols_to_remove:
                remap[j] = jnew
                jnew += 1

        new_col_types = [t for i, t in enumerate(self.col_types) if i not in cols_to_remove]
        new_var_names = [v for i, v in enumerate(self.var_names) if i not in cols_to_remove]

        new_tableau = []
        for i in range(len(self.tableau) - 1):
            new_tableau.append([
                val for j, val in enumerate(self.tableau[i]) if j not in cols_to_remove
            ])

        new_base = []
        for bv in self.base_vars:
            new_base.append(remap.get(bv, None))

        return Tableau(new_tableau, new_col_types, new_var_names, new_base, self.objective_type)

    # ==========================================================
    # Linha objetivo da Fase 2
    # ==========================================================
    def set_objective_from_original(self, c_orig, objective_type="Max"):
        total_cols = len(self.tableau[0])
        obj = [0.0] * total_cols

        orig_idx = [i for i, t in enumerate(self.col_types) if t == "orig"]

        for k, j in enumerate(orig_idx):
            if k < len(c_orig):
                obj[j] = -c_orig[k] if objective_type == "Max" else c_orig[k]

        # Ajustar com base
        for i in range(len(self.tableau) - 1):
            bv = self.base_vars[i]
            if bv is not None and abs(obj[bv]) > EPS:
                f = obj[bv]
                obj = [
                    obj[j] - f * self.tableau[i][j]
                    for j in range(total_cols)
                ]

        self.tableau.append(obj)

    # ==========================================================
    # Extração da solução expandida
    # ==========================================================
    def extract_solution_expanded(self, k):
        m = len(self.tableau) - 1
        sol = [0.0] * k

        for col in range(k):
            row = None
            ok = True
            for i in range(m):
                if abs(self.tableau[i][col] - 1) < EPS:
                    if row is not None:
                        ok = False
                        break
                    row = i
                elif abs(self.tableau[i][col]) > EPS:
                    ok = False
                    break
            sol[col] = self.tableau[row][-1] if ok and row is not None else 0.0

        return sol
