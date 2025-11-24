# simplex.py
from parser import Parser
from tableau import Tableau

EPS = 1e-9

class SimplexSolver:
    def __init__(self, model):
        if "objective_coeffs" in model:
            self.c = [float(x) for x in model["objective_coeffs"]]
        else:
            self.c = [float(x) for x in model["c"]]

        self.objective_type = model["objective_type"]
        self.constraints = model["constraints"]
        self.nonneg = model.get("non_negative", model.get("nonneg"))
        self.n = model["num_vars"]

    # ==========================================================
    # Expansão de variáveis livres (x = x⁺ - x⁻)
    # ==========================================================
    def _expand_free(self, A_rows, c, nonneg):
        mapping = []
        var_names = []
        cur = 0

        for i in range(len(c)):
            if not nonneg[i]:
                # variável livre → vira duas não-negativas
                mapping.append((cur, cur+1))
                var_names.append(f"x{i+1}_pos")
                var_names.append(f"x{i+1}_neg")
                cur += 2
            else:
                mapping.append((cur,))
                var_names.append(f"x{i+1}")
                cur += 1

        new_n = cur
        c2 = [0.0] * new_n

        # Expande objetivo
        for i in range(len(c)):
            idxs = mapping[i]
            if len(idxs) == 2:
                c2[idxs[0]] += c[i]
                c2[idxs[1]] += -c[i]
            else:
                c2[idxs[0]] += c[i]

        # Expande restrições
        A2 = []
        for row in A_rows:
            new_row = [0.0] * new_n
            for i in range(len(c)):
                idxs = mapping[i]
                if len(idxs) == 2:
                    new_row[idxs[0]] += row[i]
                    new_row[idxs[1]] += -row[i]
                else:
                    new_row[idxs[0]] += row[i]
            A2.append(new_row)

        return A2, c2, mapping, var_names

    # ==========================================================
    # Resolver
    # ==========================================================
    def solve(self, verbose=True):
        # A, comp, b
        A = [row for row, _, _ in self.constraints]
        comps = [comp for _, comp, _ in self.constraints]
        b = [bb for *_, bb in self.constraints]

        # Expande variáveis livres
        A2, c2, mapping, var_names = self._expand_free(A, self.c, self.nonneg)

        # ------------------------------------------------------
        # FASE 1: construir tableau
        # ------------------------------------------------------
        T1 = Tableau.from_phase1(A2, comps, b, orig_var_names=var_names,
                                 objective_type=self.objective_type)

        if verbose:
            print("\n--- Fase 1 (zerar artificiais) ---\n")

        status_phase1 = T1.run_simplex(verbose=verbose)

        if status_phase1 == "unbounded":
            if verbose:
                print("Fase 1: ilimitado.")
            return None

        phase1_obj = T1.tableau[-1][-1]

        if abs(phase1_obj) > 1e-7:
            if verbose:
                print("Problema inviável (valor da Fase 1 != 0).")
            return None

        # ------------------------------------------------------
        # Remover artificiais para iniciar Fase 2
        # ------------------------------------------------------
        T2 = T1.remove_artificials()

        # Criar linha OBJ (fase 2)
        # Substituir por objetivo original (não adicionar linha extra antes; método já cria a linha OBJ)
        T2.set_objective_from_original(c2, objective_type=self.objective_type)

        if verbose:
            print("\n--- Fase 2 (otimização da função objetivo original) ---\n")

        status_phase2 = T2.run_simplex(verbose=verbose)

        if status_phase2 == "unbounded":
            if verbose:
                print("Problema ilimitado (fase 2).")
            return None

        # ------------------------------------------------------
        # Recuperar solução das variáveis expandidas
        # ------------------------------------------------------
        sol_expanded = T2.extract_solution_expanded(len(c2))

        # Remapear para x originais
        orig_solution = {}
        for orig_idx, mapped in enumerate(mapping):
            if len(mapped) == 2:
                p, n = mapped
                vp = sol_expanded[p] if p < len(sol_expanded) else 0
                vn = sol_expanded[n] if n < len(sol_expanded) else 0
                orig_solution[f"x{orig_idx+1}"] = vp - vn
            else:
                idx = mapped[0]
                orig_solution[f"x{orig_idx+1}"] = sol_expanded[idx] if idx < len(sol_expanded) else 0

        # Valor ótimo
        z = T2.tableau[-1][-1]
        if self.objective_type == "Min":
            z = -z

        return {
            "z": z,
            "original_solution": orig_solution,
            "phase1_obj": phase1_obj,
            "status_phase1": status_phase1,
            "status_phase2": status_phase2
        }


# Interface simples
def run_from_input(path="input/input.txt", verbose=True):
    p = Parser(path)
    model = p.parse()
    solver = SimplexSolver(model)
    return solver.solve(verbose=verbose)

from parser import Parser
