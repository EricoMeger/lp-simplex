# main.py
from parser import Parser
from simplex import SimplexSolver

def main():
    filepath = "input/input.txt"
    parser = Parser(filepath)
    model = parser.parse()

    solver = SimplexSolver(model)
    result = solver.solve(verbose=True)

    if result is None:
        print("Problema inviável ou ilimitado.")
    else:
        print("\n=== Resultado ===")
        print("Z ótimo:", result["z"])
        print("Solução (variáveis originais):")
        for k,v in result["original_solution"].items():
            print(f"  {k} = {v:.6f}")
        print("\nDetalhes: phase1_obj =", result["phase1_obj"], ", status_phase1 =", result["status_phase1"], ", status_phase2 =", result["status_phase2"])

if __name__ == "__main__":
    main()
