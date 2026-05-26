# v0, process I used to tokenize wasnt the best
# so i changed it up for v1

import re, os, sys, time
from colorama import Fore as f, init

class Lexer():
    def __init__(self):
        init(autoreset=True) # fore
        
        self.tokens = []
        self.currentPosition = 0
        self.execution = 0
        
        self.patterns = {
            r'\s+': 'WHITESPACE',
            r'\n': 'NEWLINE',
            
            r'\d+': 'NUMBER',
            r'[a-z]+': 'LETTER',
            
            r'\+': 'PLUS',
            r'\-': 'SUBTRACT',
            r'\*': 'MULTIPLY',
            r'\/': 'DIVIDE',
            r'\(': 'OPENPARENTHESIS',
            r'\)': 'CLOSEPARENTHESIS',
            
            r'\for': 'LOOP',
            r'\print': 'PRINT',
            r'\if': 'IF',
        }
        
        self.charToRegex = {
            '0123456789': r'\d+',
            'abcdefghijklmnopqrstuvwxyz': r'[a-z]+',
        }
        
        self.lookup = {}

    def setupPatterns(self):
        self.execution = time.time()
        for characters, regex in self.charToRegex.items():
            for character in characters:
                self.lookup[character] = regex
                
        for character in "+-*/":
            val = rf'\{character}'
            self.lookup[character] = val
            
        self.lookup["\n"] = r'\n'
        self.lookup["for"] = r'\for'
        self.lookup["print"] = r'\print'
        self.lookup["("] = r'\('
        self.lookup[")"] = r'\)'
        self.lookup["\s+"] = r'\s+'
        print(self.lookup)
        
    
    def tokenizer(self, value):
        self.setupPatterns()
        operations = 0

        while (self.currentPosition < len(value)):
            try:
                character = value[self.currentPosition]
                pattern = self.lookup[character]
                tokenType = self.patterns[pattern]
                regex = re.compile(pattern)
                match = regex.match(value, self.currentPosition)
                spaces = (4 - len(str(self.currentPosition))) * " "

                print(f"{f.GREEN} {self.currentPosition}{spaces}|  {match} ({tokenType})")
                if not match:
                    raise ValueError(f"Invalid token at position {self.currentPosition}")

                self.tokens.append((f"Value: {match.group(0)}", tokenType))
                self.currentPosition = match.end()
            except:
                spaces = (4 - len(str(self.currentPosition))) * " "
                print(f" {f.RED}{self.currentPosition}{spaces}|  UNKOWN CHARACTER: \"{value[self.currentPosition]}\"")
                self.currentPosition += 1

            operations += 1

        return operations        
        
    def math_evaluation(self):
        stack = []
        operations = {
            'PLUS': '+',
            'SUBTRACT': '-',
            'MULTIPLY': '*',
            'DIVIDE': '/',
            'OPENPARENTHESIS': '(',
            'CLOSEPARENTHESIS': ')',
        }
        
        for token, token_type in self.tokens:
            if token_type == 'NUMBER':
                stack.append(int(token.split(":")[1].strip()))
                
            elif token_type in operations.keys():
                stack.append(token_type)
        
        evaluation = ""
        for item in stack:
            if item in operations.keys():
                evaluation += operations.get(item)
            else:
                evaluation += str(item)

        return [stack, eval(evaluation)]

    def main(self, value, output):
        os.system('clear')
        result = self.tokenizer(value)
        calculated_output = self.math_evaluation()

        spacer = "-"
        # output = self.evaluate_expression()
        print(f"{50*spacer}\nInput: {value}\nOutput: {calculated_output[-1]}\nLiteral: {calculated_output[0]}\n")        
        
        print(f"Execution time: {round(time.time()-self.execution, 7)}s\nOperations: {result}\n\n{self.tokens}")
    
        
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 interpreter.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]
    if filename.split(".")[1] != "rot":
        print(f"File {filename} needs to be a .rot file")
        exit(1)
    try:
        with open(filename, 'r') as file:
            expression = file.read()
            Lexer().main(expression, True)
            
    except FileNotFoundError:
        print(f"File '{filename}' not found.")
        sys.exit(1)
