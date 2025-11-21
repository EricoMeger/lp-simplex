from parser import Parser
from tableau import Tableau

def main():
    filepath = "input/input.txt"

    parser = Parser(filepath)
    result = parser.parse()
    

main()