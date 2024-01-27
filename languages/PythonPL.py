from .ProgrammingLanguage import ProgrammingLanguage


class PythonPL(ProgrammingLanguage):
    def get_import_prefix(self):
        return "import "

    def extract_documentation(self, code_lines):
        docstrings = []
        inside_docstring = False
        current_docstring = ""

        for line in code_lines:
            line = line.strip()
            if line.startswith('"""') or line.startswith("'''"):
                # single line docstring
                if len(line) > 3 and line.count('"""') > 1 or line.count("'''") > 1:
                    continue  # ignore single line docstrings
                elif inside_docstring:
                    inside_docstring = False
                    docstrings.append(current_docstring)
                    current_docstring = ""
                else:
                    inside_docstring = True
                    current_docstring += line[3:]
            elif line.endswith('"""') or line.endswith("'''"):
                inside_docstring = False
                current_docstring += '\n' + line[:-3]
                docstrings.append(current_docstring)
                current_docstring = ""
            elif inside_docstring:
                current_docstring += '\n' + line
            elif line.startswith('#'):
                continue
        return docstrings

    def get_snippet_seperator(self):
        return "\n\n"

    def get_code_quality(self):
        pass

    def get_code_lifetime(self):
        pass

    def extract_imports(self, lines):
        imports = set()
        import_lines = []
        in_import_block = False
        import_block = []
        for line in lines:
            if line.startswith("import ") or line.startswith("from ") or in_import_block:
                if "(" in line:
                    in_import_block = True
                if not in_import_block:
                    import_lines.append(line)
                if ")" in line:
                    in_import_block = False
                    if import_block:
                        import_lines.append(" ".join(import_block))
                        import_block = []
                else:
                    import_block.append(line)
        for line in import_lines:
            line = line.strip()
            if line.startswith("import ") or line.startswith("from "):
                tokens = line.replace("\n", "").replace("(", "").replace(")", "").replace(
                    ",", "").split(" ")
                if len(tokens) >= 2:
                    if tokens[0] == "import":
                        previous = ""
                        for token in tokens[1:]:
                            if token and token != "as" and previous != "as":
                                imports.add(token)
                            previous = token
                    elif tokens[0] == "from" and "import" in tokens:
                        module = tokens[1]
                        index = tokens.index("import")
                        for name in tokens[index + 1:]:
                            if name:
                                imports.add(f"{module}.{name}")
        return list(imports), import_lines
