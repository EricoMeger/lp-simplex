# parser.py
import re

class Parser:
    """
    Parser que lê arquivo input com formato:
      Max 3x1 + 5x2
      x1 + 2x2 <= 6
      3x1 + 2x2 <= 12
      x1 >= 0
      x2 free

    Retorna dicionário com:
      {
        "objective_type": "Max"/"Min",
        "objective_coeffs": [...],
        "constraints": [(row, comp, b), ...],
        "num_vars": n,
        "non_negative": [...]
      }
    """

    def __init__(self, filepath):
        self.filepath = filepath

    def parse(self):
        lines = [line.strip() for line in open(self.filepath, encoding="utf-8") if line.strip() and not line.strip().startswith("#")]
        if not lines:
            raise ValueError("Arquivo vazio")

        # objective
        obj_line = lines[0]
        if obj_line.lower().startswith("max"):
            obj_type = "Max"
            rest = obj_line[3:].strip()
        elif obj_line.lower().startswith("min"):
            obj_type = "Min"
            rest = obj_line[3:].strip()
        else:
            raise ValueError("Função objetivo deve começar com 'Max' ou 'Min'")

        obj_coeffs = {}
        for raw_coeff, var in re.findall(r'([+-]?\s*\d*)x(\d+)', rest):
            coeff = raw_coeff.replace(" ", "")
            if coeff == "" or coeff == "+":
                c = 1
            elif coeff == "-":
                c = -1
            else:
                c = int(coeff)
            idx = int(var)
            obj_coeffs[idx] = obj_coeffs.get(idx, 0) + c

        constraints = []
        nonneg = {}

        for line in lines[1:]:
            m_free = re.match(r'^x(\d+)\s+(free|livre)$', line, re.I)
            m_nonneg = re.match(r'^x(\d+)\s*>=\s*0$', line)
            if m_free:
                var = int(m_free.group(1))
                nonneg[var] = False
                continue
            if m_nonneg:
                var = int(m_nonneg.group(1))
                nonneg[var] = True
                continue

            if "<=" in line or ">=" in line or "=" in line:
                coeff_map = {}
                for raw_coeff, var in re.findall(r'([+-]?\s*\d*)x(\d+)', line):
                    coeff = raw_coeff.replace(" ", "")
                    if coeff == "" or coeff == "+":
                        c = 1
                    elif coeff == "-":
                        c = -1
                    else:
                        c = int(coeff)
                    idx = int(var)
                    coeff_map[idx] = coeff_map.get(idx, 0) + c

                if "<=" in line:
                    comp = "<="
                elif ">=" in line:
                    comp = ">="
                else:
                    comp = "="

                b_match = re.search(r'(-?\d+)\s*$', line)
                if not b_match:
                    raise ValueError("Não foi possível ler RHS na linha: " + line)
                b = int(b_match.group(1))

                constraints.append((coeff_map, comp, b))

        all_idx = set(obj_coeffs.keys())
        for cm,_,_ in constraints:
            all_idx |= set(cm.keys())
        all_idx |= set(nonneg.keys())
        n = max(all_idx) if all_idx else 0

        c = [0.0]*n
        for i in range(1, n+1):
            c[i-1] = float(obj_coeffs.get(i, 0))

        constraints_vec = []
        for coeff_map, comp, b in constraints:
            row = [0.0]*n
            for i in range(1, n+1):
                row[i-1] = float(coeff_map.get(i, 0))
            constraints_vec.append((row, comp, float(b)))

        nonneg_list = []
        for i in range(1, n+1):
            nonneg_list.append(nonneg.get(i, True))

        return {
            "objective_type": obj_type,
            "objective_coeffs": c,
            "constraints": constraints_vec,
            "num_vars": n,
            "non_negative": nonneg_list
        }
