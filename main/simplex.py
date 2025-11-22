# tableau.py
class Tableau:
    def __init__(self, tableau_rows, col_types, var_names, base_vars, objective_type="Max"):
        """
        tableau_rows: lista de linhas (cada linha já inclui RHS como última coluna)
        col_types: lista de strings para cada coluna (ex: 'orig','slack','surplus','artificial')
        var_names: nomes das colunas (sem RHS)
        base_vars: lista length = m com índices das colunas básicas (ou None)
        """
        self.tableau = [row[:] for row in tableau_rows]
        self.col_types = col_types[:]
        self.var_names = var_names[:]
        self.base_vars = base_vars[:]
        self.objective_type = objective_type

    # ---- Mantive e aperfeiçoei seu build_tableau/print_tableau ----
    @classmethod
    def from_phase1(cls, A, comps, b, orig_var_names=None, objective_type="Max"):
        """
        Constrói o tableau inicial de fase 1 (com slacks/surplus/artificiais).
        Retorna instância de Tableau pronta para rodar fase 1.
        """
        m = len(A)
        n = len(A[0]) if m > 0 else 0
        tableau = [row[:] for row in A]
        col_types = ['orig'] * n
        var_names = orig_var_names[:] if orig_var_names is not None else [f"x{j+1}" for j in range(n)]
        base_vars = [None]*m
        slack_count = 0
        artificial_count = 0

        for i, comp in enumerate(comps):
            if comp == "<=":
                for r in range(m):
                    tableau[r].append(1.0 if r == i else 0.0)
                col_types.append('slack')
                var_names.append(f"s{slack_count+1}")
                base_vars[i] = n + slack_count
                slack_count += 1
            elif comp == ">=":
                for r in range(m):
                    tableau[r].append(-1.0 if r == i else 0.0)
                col_types.append('surplus')
                var_names.append(f"e{slack_count+1}")
                slack_count += 1
                for r in range(m):
                    tableau[r].append(1.0 if r == i else 0.0)
                col_types.append('artificial')
                var_names.append(f"a{artificial_count+1}")
                base_vars[i] = n + slack_count
                artificial_count += 1
                slack_count += 1
            elif comp == "=":
                for r in range(m):
                    tableau[r].append(1.0 if r == i else 0.0)
                col_types.append('artificial')
                var_names.append(f"a{artificial_count+1}")
                base_vars[i] = n + slack_count
                artificial_count += 1
                slack_count += 1
            else:
                raise ValueError("Comparator desconhecido: " + str(comp))

        # append RHS
        for i in range(m):
            tableau[i].append(b[i])

        # Build phase1 objective (maximize -sum(artificiais))
        total_cols = len(tableau[0])
        obj_row = [0.0]*total_cols
        for j,t in enumerate(col_types):
            if t == 'artificial':
                obj_row[j] = -1.0
        obj_row[-1] = 0.0
        tableau.append(obj_row)

        # if artificials are basic, add their rows to objective (to make objective consistent)
        for i in range(m):
            bv = base_vars[i]
            if bv is not None and bv < len(col_types) and col_types[bv] == 'artificial':
                tableau[-1] = [tableau[-1][j] + tableau[i][j] for j in range(len(tableau[0]))]

        return cls(tableau, col_types, var_names, base_vars, objective_type=objective_type)

    # ---- impressão (mantive seu estilo com pequenas melhorias) ----
    def print_tableau(self, iteration=0):
        m = len(self.tableau) - 1
        n = len(self.tableau[0])
        header = ["VB"] + self.var_names + ["b"]
        largura = 10
        print(f"=== Iteracao: {iteration} ===")
        print(f"{header[0]:>8}", end="")
        for h in header[1:]:
            print(f"{h:>{largura}}", end="")
        print()
        for i in range(m):
            vb_idx = self.base_vars[i]
            vb = self.var_names[vb_idx] if (vb_idx is not None and vb_idx < len(self.var_names)) else f"v{vb_idx}"
            print(f"{vb:>8}", end="")
            for val in self.tableau[i]:
                print(f"{val:>{largura}.4f}", end="")
            print()
        print(f"{'OBJ':>8}", end="")
        for val in self.tableau[-1]:
            print(f"{val:>{largura}.4f}", end="")
        print("\n")

    # ---- operações de pivô / seleção ----
    def find_pivot(self):
        last = self.tableau[-1]
        min_val = min(last[:-1])
        if min_val >= -EPS:
            return None
        pivot_col = last[:-1].index(min_val)
        ratios = []
        for i in range(len(self.tableau)-1):
            aij = self.tableau[i][pivot_col]
            if aij > EPS:
                ratios.append((self.tableau[i][-1] / aij, i))
        if not ratios:
            return ("unbounded", pivot_col)
        ratios.sort(key=lambda x: (x[0], x[1]))
        return (ratios[0][1], pivot_col)

    def pivot(self, pivot_row, pivot_col):
        m = len(self.tableau)
        n = len(self.tableau[0])
        pv = self.tableau[pivot_row][pivot_col]
        self.tableau[pivot_row] = [v / pv for v in self.tableau[pivot_row]]
        for i in range(m):
            if i == pivot_row:
                continue
            factor = self.tableau[i][pivot_col]
            self.tableau[i] = [self.tableau[i][j] - factor*self.tableau[pivot_row][j] for j in range(n)]
        # update base var for pivot_row
        self.base_vars[pivot_row] = pivot_col

    def run_simplex(self, verbose=True, max_iter=500):
        it = 0
        while True:
            it += 1
            if verbose:
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

    # ---- remover artificiais (após fase1) ----
    def remove_artificials(self):
        # remove columns marcadas como 'artificial'
        cols_to_remove = [i for i,t in enumerate(self.col_types) if t == 'artificial']
        remap = {}
        jnew = 0
        for j in range(len(self.col_types)):
            if j not in cols_to_remove:
                remap[j] = jnew
                jnew += 1

        new_col_types = [t for i,t in enumerate(self.col_types) if i not in cols_to_remove]
        new_var_names = [v for i,v in enumerate(self.var_names) if i not in cols_to_remove]

        new_tableau = []
        for i in range(len(self.tableau)-1):  # exclude objective row
            new_row = [val for j,val in enumerate(self.tableau[i]) if j not in cols_to_remove]
            new_tableau.append(new_row)

        # update base_vars: if removed, set to None
        new_base_vars = []
        for bv in self.base_vars:
            if bv is None:
                new_base_vars.append(None)
            elif bv in remap:
                new_base_vars.append(remap[bv])
            else:
                new_base_vars.append(None)

        return Tableau(new_tableau, new_col_types, new_var_names, new_base_vars, objective_type=self.objective_type)

    # ---- configurar objetivo original na tabela fase2 ----
    def set_objective_from_original(self, c_orig, objective_type="Max"):
        # c_orig: lista de coeficientes correspondentes às primeiras colunas 'orig' (após expansão de var livres)
        # Identifica quais colunas atuais correspondem a originais: assumimos que col_types começa com 'orig' para as originais
        # Construir linha objetivo
        total_cols = len(self.tableau[0])
        obj = [0.0]*total_cols
        # número de originais é o número de 'orig' presentes no col_types
        orig_indices = [i for i,t in enumerate(self.col_types) if t == 'orig']
        for idx, orig_col in enumerate(orig_indices):
            if idx < len(c_orig):
                coeff = c_orig[idx]
                obj[orig_col] = -coeff if objective_type == "Max" else coeff
        obj[-1] = 0.0
        # tornar consistente com base atual
        for i in range(len(self.tableau)-1):
            bv = self.base_vars[i]
            if bv is not None and abs(obj[bv]) > EPS:
                factor = obj[bv]
                obj = [obj[j] - factor*self.tableau[i][j] for j in range(total_cols)]
        # substituir linha objetivo
        self.tableau[-1] = obj

    # ---- extrair solucao para as primeiras "k" colunas (expanded) ----
    def extract_solution_expanded(self, k):
        m = len(self.tableau)-1
        sol = [0.0]*k
        for col in range(k):
            # verificar se coluna é basica
            count_one = 0
            row_index = None
            for i in range(m):
                if abs(self.tableau[i][col] - 1.0) < 1e-8:
                    count_one += 1
                    row_index = i
                elif abs(self.tableau[i][col]) > 1e-8:
                    count_one = -1000
            if count_one == 1:
                sol[col] = self.tableau[row_index][-1]
            else:
                sol[col] = 0.0
        return sol
