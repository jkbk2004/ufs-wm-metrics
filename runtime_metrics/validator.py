import ast
import os
import re

def check_syntax(file_path):
    try:
        with open(file_path) as f:
            source = f.read()
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, f"{file_path}: SyntaxError on line {e.lineno}: {e.msg}"

def check_docstrings(file_path):
    with open(file_path) as f:
        source = f.read()
    tree = ast.parse(source)
    missing = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if not ast.get_docstring(node):
                missing.append(f"{file_path}: Missing docstring in function '{node.name}'")
    return missing

def check_regex_literals(file_path):
    with open(file_path) as f:
        lines = f.readlines()
    issues = []
    for i, line in enumerate(lines):
        if "re.search(r\"" in line and not line.strip().endswith(")") and "\"" not in line.strip()[len("re.search(r\""):]:
            issues.append(f"{file_path}: Possibly unterminated regex on line {i+1}")
    return issues

def validate_directory(directory):
    all_files = [f for f in os.listdir(directory) if f.endswith(".py")]
    for file in all_files:
        path = os.path.join(directory, file)
        ok, err = check_syntax(path)
        if not ok:
            print(f"❌ {err}")
        else:
            print(f"✅ {file}: Syntax OK")
        for issue in check_docstrings(path):
            print(f"⚠️ {issue}")
        for issue in check_regex_literals(path):
            print(f"⚠️ {issue}")

if __name__ == "__main__":
    validate_directory(".")
