# simplex.py
from parser import Parser
from tableau import Tableau
import copy

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

    def _expand_free(self, A_rows, c, nonneg):
        mapping = []
        var_names = []
        cur = 0
        for i in range(len(c)):
            if not nonneg[i]:
                mapping.append((cur, cur+1))
                var_names.append(f"x{i+1}_pos")
                var_names.append(f"x{i+1}_neg")
                cur += 2
            else:
                mapping.append((cur,))
                var_names.append(f"x{i+1}")
                cur += 1
        new_n = cur
        c2 = [0.0]*new_n
        for i in range(len(c)):
            idxs = mapping[i]
            if len(idxs) == 2:
                c2[idxs[0]] += c[i]
                c2[idxs[1]] += -c[i]
            else:
                c2[idxs[0]] += c[i]
        A2 = []
        for row in A_rows:
            new_row = [0.0]*new_n
            for i in range(len(c)):
                idxs = mapping[i]
                if len(idxs) == 2:
                    new_row[idxs[0]] += row[i]
                    new_row[idxs[1]] += -row[i]
                else:
                    new_row[idxs[0]] += row[i]
            A2.append(new_row)
        return A2, c2, mapping, var_names

    def solve(self, verbose=True):
        A = [row for row,_,_ in self.constraints]
        comps = [comp for _,comp,_ in self.constraints]
        b = [bb for *_,bb in [ (r,c,bb) for r,c,bb in self.constraints]]

        # expand free vars
        A2, c2, mapping, var_names = self._expand_free(A, self.c, self.nonneg)

        # build phase1 tableau
        T1 = Tableau.from_phase1(A2, comps, b, orig_var_names=var_names, objective_type=self.objective_type)

        if verbose:
            print("\n--- Fase 1 (zerar artificiais) ---\n")
        status1 = T1.run_simplex(verbose=verbose)
        if status1 == "unbounded":
            if verbose: print("Fase 1: ilimitado")
            return None
        phase1_obj = T1.tableau[-1][-1]
        if abs(phase1_obj) > 1e-8:
            if verbose: print("Problema inviável (fase1 != 0). Valor:", phase1_obj)
            return None

        # Remove artificiais (robusto)
        T2 = T1.remove_artificials()

        print("\n--- DEBUG: Tableau após remove_artificials() ---")
        for row in T2.tableau:
            print(row)
        print("Base:", T2.base_vars)
        print("Variáveis:", T2.var_names)
        print("Tipos:", T2.col_types)

        # Append objective row placeholder (zeros) to T2.tableau for consistent shape
        # Ensure objective row exists with correct length
        if len(T2.tableau) == 0 or len(T2.tableau[-1]) != len(T2.tableau[0]):
            # build a zero objective row with RHS zero
            obj_row = [0.0]*len(T2.tableau[0])
            T2.tableau.append(obj_row)
        else:
            # ensure there's an objective row (if not present)
            if len(T2.tableau) == len(T2.tableau[0]):
                T2.tableau.append([0.0]*len(T2.tableau[0]))

        # Set original objective
        T2.set_objective_from_original(c2, objective_type=self.objective_type)

        if verbose:
            print("\n--- Fase 2 (otimização da função objetivo original) ---\n")
        status2 = T2.run_simplex(verbose=verbose)
        if status2 == "unbounded":
            if verbose: print("Problema ilimitado (fase2).")
            return None

        # extract expanded solution
        orig_count = len(c2)
        sol_expanded = T2.extract_solution_expanded(orig_count)

        # map back to original variables
        orig_solution = {}
        for orig_idx, mapped in enumerate(mapping):
            if len(mapped) == 2:
                p, n = mapped
                vp = sol_expanded[p] if p < len(sol_expanded) else 0.0
                vn = sol_expanded[n] if n < len(sol_expanded) else 0.0
                orig_solution[f"x{orig_idx+1}"] = vp - vn
            else:
                idx = mapped[0]
                orig_solution[f"x{orig_idx+1}"] = sol_expanded[idx] if idx < len(sol_expanded) else 0.0

        z = T2.tableau[-1][-1]
        if self.objective_type == "Min":
            z = -z

        return {
            "z": z,
            "original_solution": orig_solution,
            "phase1_obj": phase1_obj,
            "status_phase1": status1,
            "status_phase2": status2
        }

def run_from_input(path="input/input.txt", verbose=True):
    p = Parser(path)
    model = p.parse()
    solver = SimplexSolver(model)
    return solver.solve(verbose=verbose)

# Expose Parser for run_from_input
from parser import Parser
