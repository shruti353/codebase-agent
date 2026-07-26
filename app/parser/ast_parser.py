# def parse_file(filepath: str) -> list[dict]:
#     """Returns a list of dicts, one per function/class found in file:
    
#     { "name": ..., "type": "function": | "class", "docstring":...,
#     "source_code":..., "file": filepath, "start_line": ..., "end_line": ...
#     }

#     """
#     # 1. read the file text
#     # 2. ast.parse() it
#     # 3. ast.walk() the tree
#     # 4. for each FunctionDef / AsyncFunctionDef / ClassDef node, build the dict
#     # 5. return the list
    

import ast
from pathlib import Path

SKIP_DIRS = {"venv", ".venv", ".git", "__pycache__", "node_modules"}
    
class CodeVisitor(ast.NodeVisitor):
    def __init__(self,source,filepath):
        self.source= source
        self.filepath= filepath
        self.chunks= []
        self.calls =[]
        self.current_class= None
        self.current_function= None
        
    def find_calls_in(self,fun_node):
            calls=[]
            for node in ast.walk(fun_node):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        calls.append(node.func.id)
                    elif isinstance(node.func, ast.Attribute):
                        calls.append(node.func.attr)
                        
            return calls
            
        
    def visit_ClassDef(self,node):
        entry= {
            "name": node.name,
            "type": "class",
            "docstring":ast.get_docstring(node),
            "source_code": ast.get_source_segment(self.source, node),
            "file": self.filepath,
            "start_line":node.lineno,
            "end_line":node.end_lineno,
            "parent_class":None
        }
        self.chunks.append(entry)
        
        prev_class= self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class= prev_class
        
    def visit_FunctionDef(self,node):
        entry={
                    "name": node.name,
                    "type": "function",
                    "docstring":ast.get_docstring(node),
                    "source_code": ast.get_source_segment(self.source, node),
                    "file": self.filepath,
                    "start_line":node.lineno,
                    "end_line":node.end_lineno,
                    "parent_class":self.current_class

        }
        self.chunks.append(entry)
        
        for callee in self.find_calls_in(node):
            self.calls.append((node.name, callee))
        
        prev_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev_function
        
    visit_AsyncFunctionDef = visit_FunctionDef
    
def find_python_files(repo_path):
    for path in Path(repo_path).rglob("*.py"):
        if not any(part in SKIP_DIRS for part in path.parts):
            yield path
            
def parse_repo(repo_path):
    all_chunks=[]
    all_calls=[]

    for file_path in find_python_files(repo_path):
        with open(file_path, "r", encoding="utf-8") as f:
            source= f.read()
        
        try:
            tree= ast.parse(source)
        except SyntaxError:
            print(f"Skipping {file_path}: could not parse")
            continue
        
        visitor= CodeVisitor(source, str(file_path))
        visitor.visit(tree)
        
        all_chunks.extend(visitor.chunks)
        all_calls.extend(visitor.calls)
        
    return all_chunks, all_calls

           

if __name__=="__main__":
    import json
    
    chunks, calls = parse_repo(".")
    
    print(f"found {len(chunks)} chunks and {len(calls)} calls \n")
    print(json.dumps(chunks,indent=2))
    print(calls)
    