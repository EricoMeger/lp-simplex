import re

class Parser:
    """
    Max 2x1 + 3x2 
    2x1 + x2 <= 10
    x1 + 3x2 <= 5
    x1 >= 0
    x2 >= 0
    """

    def __init__(self, filepath):
        self.filepath = filepath
        self.objective_type = None 
        self.objective_coeffs = []
        self.constraints = []
        self.num_vars = 0
        self.non_negative = []
        self.var_signs = []

    def parse(self):
        lines = [line.strip() for line in open(self.filepath)]

        idx = None
        for i, l in enumerate(lines):
            ll = l.lower()
            if ll.startswith("max") or ll.startswith("min"):
                idx = i
                break
        if idx is None:
            raise ValueError("Objective function must be Max or Min.")

        self.parse_objective(lines[idx])

        for line in lines[idx+1:]:
            if not line:
                continue
            if self.is_non_negative(line):
                self.parse_non_negative(line)
            elif "<=" in line or ">=" in line or "=" in line:
                self.parse_constraint(line)

        #if some variables were not mentioned in non-negativity constraints, assume they are non-negative
        while len(self.non_negative) < self.num_vars:
            self.non_negative.append(True)
        while len(self.var_signs) < self.num_vars:
            self.var_signs.append(">=0")

        return {
            "objective_type": self.objective_type,
            "objective_coeffs": self.objective_coeffs,
            "constraints": self.constraints,
            "num_vars": self.num_vars,
            "non_negative": self.non_negative,
            "var_signs": self.var_signs
        }
        
    def is_non_negative(self, line):
        """
        x\d+\s*(>=|<=)\s*0$:
            x\d+      - 'x' followed by one or more digits (variable index, e.g. x1, x2)
            \s*       - any number of spaces
            (>=|<=)   - either the ">=" or "<=" comparison operator
            \s*       - any number of spaces
            0         - the numeric bound zero
            $         - end of line anchor to ensure the entire tail matches (so it wont match extra trailing chars)

        This pattern matches lines like: "x1 >= 0" or "x2 <= 0".
        In addition, we also treat lines containing the word "livre" (Portuguese for "free")
        as indicating a free variable (no sign restriction).
        """
        return re.match(r"x\d+\s*(>=|<=)\s*0$", line) is not None or "livre" in line.lower()
    
    def parse_non_negative(self, line):
        var_match = re.findall(r"x(\d+)", line)
        if not var_match:
            return
            
        var = int(var_match[0])
        
        self.num_vars = max(self.num_vars, var)
        
        while len(self.non_negative) < var:
            self.non_negative.append(True)
        while len(self.var_signs) < var:
            self.var_signs.append(">=0")
        
        if "livre" in line.lower():
            self.non_negative[var - 1] = False
            self.var_signs[var - 1] = "free"
        elif "<=" in line:
            self.non_negative[var - 1] = False
            self.var_signs[var - 1] = "<=0"
        else:
            self.non_negative[var - 1] = True
            self.var_signs[var - 1] = ">=0"
    
    def parse_objective(self, line):
        line_lower = line.lower()
        if line_lower.startswith("max"):
            self.objective_type = "Max"
        elif line_lower.startswith("min"):
            self.objective_type = "Min"
        else:
            raise ValueError("Objective function must be Max or Min.")

        """
        Explaining the regex:
        ([+-]?\s*\d*) - 1st step, we search for the coefficient of the variable:
            [+-]?      - an optional '+' or '-' sign
            \s*        - followed by any number of spaces
            \d*        - followed by any number of digits (the coefficient itself)
        \s*x\s*(\d+)       - 2nd step, we look for the variable part:
            \s*        - any number of spaces
            x          - the character 'x' indicating a variable
            \s*        - any number of spaces
            (\d+)      - followed by one or more digits (the variable index, e.g. x1, x2, etc.)
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
            
        """
        (-?\d+)$
            -? - matches an optional negative sign
            \d+ - matches one or more digits
            $ - guarantees that the match is at the end of the line
        """
        b = int(re.findall(r'(-?\d+)$', line)[0])

        self.constraints.append((parsed, comp, b))
