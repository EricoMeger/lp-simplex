# Método Simplex para Problemas Básicos

def Ler_Modelo():

    """
    Max Z = 3*x1 + 2*x2
    s.a
    [R1]    2*x1 + 1*x2 = 6
    [R2]    3*x1 + 2*x2 <= 12
              x1, x2 < 0
    """
    c = [3, 2]
    A = [[2, 1],
         [3, 2]]
    b = [6, 12]
    VD = ['x1', 'x2']

    return c, A, b, VD

def Imprimir_Tableau(Base, Iter, Variaveis, Tableau):

    Cabecalho = ['VB', '-Z'] + Variaveis + ['b']
    Largura = 6 #para as colunas numéricas

    # Impressão
    print(f'=== Iteracao: {Iter} ===')
    print(f'{Cabecalho[0]:>15}', end="")
    for elemento in Cabecalho[1:]:
        print(f'{elemento:>{Largura}}', end="")
    print()

    # Impressão das Variáveis Básicas
    for i, var in enumerate(Base):
        print(f'{var:>15}', end="")
        for valor in Tableau[i]:
            print(f'{valor:>{Largura}.2f}', end="")
        print()
    
    # Impressão da FO
    print(f'{"-Z":>15}', end="")
    for valor in Tableau[-1]:
        print(f'{valor:>{Largura}.2f}', end="")
    print()

def Metodo_Simplex(c, A, b, VD):

    # Contando VDs e Restrições
    m = len(A) # Número de Restrições
    n = len(c) # Número de VDs

    # Coeficiente das Restrições
    Tableau = []
    for i in range(m):
        linha = [0] + A[i][:] + [0]*m + [b[i]]
        linha[n + i + 1] = 1
        Tableau.append(linha)
    
    # Coeficientes da FO
    linha_FO = [1] + [-j for j in c] + [0]*m + [0]
    Tableau.append(linha_FO)

    # Nomeando as variáveis de folga
    Folgas = [f'w{i+1}' for i in range(m)]
    VD_Folgas = VD + Folgas
    Base = Folgas[:]

    Iter = 0
    Imprimir_Tableau(Base, Iter, VD_Folgas, Tableau)
    print()

    # Loop Principal
    while True:
        Z_Linha = Tableau[-1][1:-1] # última linha do tableau, da primeira até a última coluna
        Menor_Coef = min(Z_Linha) # Captura o coeficiente mais negativo

        if Menor_Coef >= 0: # Critério de Parada
            print('\nSolução Ótima Encontrada')
            break

        # Identificando a Variável que Entrará na Base
        Coluna_Pivo = Z_Linha.index(Menor_Coef) + 1

        # Identificando a Variável que Sairá da Base
        Vetor_Bloqueio = []
        for i in range(m):
            if Tableau[i][Coluna_Pivo] > 0:
                Valor_Bloq = Tableau[i][-1] / Tableau[i][Coluna_Pivo]
            else:
                Valor_Bloq = float("inf")
            Vetor_Bloqueio.append(Valor_Bloq)
        Linha_Pivo = Vetor_Bloqueio.index(min(Vetor_Bloqueio))

        # Identificando Solução Ilimitada
        if min(Vetor_Bloqueio) == float("inf"):
            print('\nSolução Ilimitada')
            return
        
        # Normalização da Linha Pivô
        Pivo = Tableau[Linha_Pivo][Coluna_Pivo]
        for j in range(len(Tableau[Linha_Pivo])):
            Tableau[Linha_Pivo][j] = (Tableau[Linha_Pivo][j] / Pivo)

        # Zerando as colunas acima e abaixo da linha pivô (escalonamento de Gauss)
        for i in range(len(Tableau)):
            if i != Linha_Pivo:
                Fator = Tableau[i][Coluna_Pivo]
                for j in range(len(Tableau[1])):
                    Tableau[i][j] = Tableau[i][j] - Fator*Tableau[Linha_Pivo][j]
        
        # Atualizando a Base
        Base[Linha_Pivo] = VD_Folgas[Coluna_Pivo - 1]

        Iter = Iter + 1
        Imprimir_Tableau(Base, Iter, VD_Folgas, Tableau)
        print()

        

if __name__ == "__main__":
    c, A, b, VD = Ler_Modelo()
    Metodo_Simplex(c, A, b, VD)