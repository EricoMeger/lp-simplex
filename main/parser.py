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

    def parse(self):
        lines = [line.strip() for line in open(self.filepath)]

        self.parse_objective(lines[0])

        for line in lines[1:]:
            if "<=" in line or ">=" in line or "=" in line:
                self.parse_constraint(line)

        return {
            "objective_type": self.objective_type,
            "objective_coeffs": self.objective_coeffs,
            "constraints": self.constraints,
            "num_vars": self.num_vars
        }

    def parse_objective(self, line):
        if line.startswith("Max"):
            self.objective_type = "Max"
        elif line.startswith("Min"):
            self.objective_type = "Min"
        else:
            raise ValueError("Objective function must be Max or Min.")

        """
        Explaining the regex:
        ([+-]?\s*\d*) - 1st step, we search for the coefficient of the variable:
            [+-]?      - an optional '+' or '-' sign
            \s*        - followed by any number of spaces
            \d*        - followed by any number of digits (the coefficient itself)
        x(\d+)       - 2nd step, we look for the variable part:
            x          - the character 'x' indicating a variable
            (\d+)      - followed by one or more digits (the variable index, e.g. x1, x2, etc.)
        """

        coeffs = re.findall(r'([+-]?\s*\d*)x(\d+)', line)
        #after we have found all coefficients and variable indices, we iterate over them to process each pair:
        for raw_coeff, var in coeffs:
            raw_coeff = raw_coeff.replace(" ", "") #if we have some spaces, like "+ 3", we remove them
            if raw_coeff == '+' or raw_coeff == '' or raw_coeff == '+ ':
                raw_coeff = 1
            elif raw_coeff == '-':
                raw_coeff = -1
            else:
                raw_coeff = int(raw_coeff)
            var = int(var)
            self.num_vars = max(self.num_vars, var)
            #consider an edge case where the coefficients are not in order, like "Max 3x3 + 2x1 + x2"
            #we store them as tuples (variable index, coefficient) to sort them later
            self.objective_coeffs.append((var, raw_coeff))

        self.objective_coeffs = [c for _, c in sorted(self.objective_coeffs)]

    def parse_constraint(self, line):
        coeffs = re.findall(r'([+-]?\s*\d*)x(\d+)', line)
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
