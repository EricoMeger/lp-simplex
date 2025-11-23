from parser import Parser
from simplex import Simplex

def main():
    filepath = "input/input.txt"

    parser = Parser(filepath)
    result = parser.parse()
    
    print("="*80)
    print(f"Tipo: {result['objective_type']}")
    print(f"Função Objetivo: {result['objective_coeffs']}")
    print(f"Número de variáveis: {result['num_vars']}")
    print(f"Restrições: {result['constraints']}")
    print("="*80 + "\n")
    
    simplex = Simplex(
        objective_coeffs=result['objective_coeffs'],
        constraints=result['constraints'],
        objective_type=result['objective_type'],
        non_negative=result['non_negative']
    )
    
    solution = simplex.solve()
    
    print()
    print("="*80)
    print("RESULTADO")
    print("="*80)
    print()
    print(f"Status: {solution['status']}")
    
    if solution['status'] == 'optimal':
        print(f"Valor ótimo: {solution['optimal_value']:.4f}")
        print("Solução ótima:")
        for i, val in enumerate(solution['solution'], start=1):
            print(f"  x{i} = {val:.4f}")
    elif solution['status'] == 'unbounded':
        print("O problema é ILIMITADO (unbounded)")
    elif solution['status'] == 'infeasible':
        print("O problema é INVIÁVEL (infeasible)")
    else:
        print(f"Status desconhecido: {solution['status']}")
    
    print("="*80)
    

if __name__ == "__main__":
    main()