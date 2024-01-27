import re

from .CppPL import CppPL


class CSharpPL(CppPL):

    def get_import_prefix(self):
        return "using "

    def extract_imports(self, lines):
        pattern = r'using\s+([\w\.]+);'
        libraries = []
        import_lines = []
        for line in lines:
            matches = re.findall(pattern, line)
            if matches:
                import_lines.append(line)
                library_names = [match for match in matches]
                libraries.extend(library_names)
        return libraries, import_lines
