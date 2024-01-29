import re

from .CppPL import CppPL


class CSharpPL(CppPL):

    def get_import_prefix(self):
        return "using "

    def extract_imports(self, lines):
        pattern = r'using\s+([\w\.]+);'
        libraries = []
        for line in lines:
            matches = re.findall(pattern, line)
            if matches:
                library_names = [match for match in matches]
                libraries.extend(library_names)
        return libraries
