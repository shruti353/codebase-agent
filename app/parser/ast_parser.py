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
def parse_file(filepath:str)-> list[dict]:
    with open(filepath, "r", encoding="utf-8") as f:
        source= f.read()
    tree= ast.parse(source)
    
    print(tree)
    print(ast.dump(tree))
    
    class CodeVisitor(ast.NodeVisitor):
        def __init__(self,source,filepath):
            self.source= source
            self.filepath= filepath
            self.chunks= []
            self.calls =[]
            self.current_class= None
            self.current_function= None
            
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
            
            def visit_FucntionDef(self,node):
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
                
                for call in self.find_calls_in(node):
                    self.calls.append((node.name, call))
                
                prev_function = self.current_function
                self.current_function = node.name
                self.generic_visit(node)
                self.current_function = prev_function

            visit_AsyncFunctionDef = visit_FunctionDef
            
        
    results=[]
    for node in ast.walk(tree):
        if isinstance (node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            entry={
                "name":node.name,
                "type": "class" if isinstance(node,ast.ClassDef) else "function",
                "docstring": ast.get_docstring(node),
                "source_code":ast.get_source_segment(source,node),
                "file":filepath,
                "start_line":node.lineno,
                "end_line":node.end_lineno   
                
                }
            results.append(entry)
    return results


if __name__=="__main__":
    import json
    parsed= parse_file("sample.py")
    print(json.dumps(parsed, indent=2))
    