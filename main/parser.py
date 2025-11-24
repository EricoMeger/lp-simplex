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
        lines = [line.strip() for line in open(self.filepath)]

        self.parse_objective(lines[0])

        for line in lines[1:]:
            if self.is_non_negative(line):
                self.parse_non_negative(line)
            elif "<=" in line or ">=" in line or "=" in line:
                self.parse_constraint(line)

        #if some variables were not mentioned in non-negativity constraints, assume they are non-negative
        while len(self.non_negative) < self.num_vars:
            self.non_negative.append(True)

        return {
            "objective_type": self.objective_type,
            "objective_coeffs": self.objective_coeffs,
            "constraints": self.constraints,
            "num_vars": self.num_vars,
            "non_negative": self.non_negative
        }
        
    def is_non_negative(self, line):
        return re.match(r"x\d+\s*(>=|<=)\s*0$", line) is not None or "livre" in line.lower()
    
    def parse_non_negative(self, line):
        var_match = re.findall(r"x(\d+)", line)
        if not var_match:
            return
            
        var = int(var_match[0])
        
        self.num_vars = max(self.num_vars, var)
        
        while len(self.non_negative) < var:
            self.non_negative.append(True)
        
        if "livre" in line.lower():
            self.non_negative[var - 1] = False
        elif "<=" in line:
            self.non_negative[var - 1] = False
        else:
            self.non_negative[var - 1] = True
    
    def parse_objective(self, line):
        line_lower = line.lower()
        if line_lower.startswith("max"):
            self.objective_type = "Max"
        elif line_lower.startswith("min"):
            self.objective_type = "Min"
        else:
            raise ValueError("Objective function must be Max or Min.")

        """
        Regex atualizado para aceitar espaços entre coeficiente e variável:
        ([+-]?\s*\d*)\s* - coeficiente com possíveis espaços após
        x\s*(\d+)        - 'x' seguido de possíveis espaços e depois o índice
        
        Exemplos que funciona:
        - "3x1"     (sem espaço)
        - "3 x1"    (com espaço)
        - "+ 3x1"   (sinal com espaço)
        - "+3 x1"   (combinação)
        """
        coeffs = re.findall(r'([+-]?\s*\d*)\s*x\s*(\d+)', line)
        
        for raw_coeff, var in coeffs:
            raw_coeff = raw_coeff.replace(" ", "")
            if raw_coeff == '+' or raw_coeff == '' or raw_coeff == '+ ':
                raw_coeff = 1
            elif raw_coeff == '-':
                raw_coeff = -1
            else:
                raw_coeff = int(raw_coeff)
            var = int(var)
            self.num_vars = max(self.num_vars, var)
            self.objective_coeffs.append((var, raw_coeff))

        self.objective_coeffs = [c for _, c in sorted(self.objective_coeffs)]

    def parse_constraint(self, line):
        coeffs = re.findall(r'([+-]?\s*\d*)\s*x\s*(\d+)', line)
        parsed = [0] * (self.num_vars)

        for raw_coeff, var in coeffs:
            raw_coeff = raw_coeff.replace(" ", "")
            if raw_coeff == '' or raw_coeff == '+':
                raw_coeff = 1
            elif raw_coeff == '-':
                raw_coeff = -1
            else:
                raw_coeff = int(raw_coeff)

            var = int(var)
            parsed[var - 1] = raw_coeff

                if "<=" in line:
                    comp = "<="
                elif ">=" in line:
                    comp = ">="
                else:
                    comp = "="

        b = int(re.findall(r'(-?\d+)$', line)[0])

        self.constraints.append((parsed, comp, b))
