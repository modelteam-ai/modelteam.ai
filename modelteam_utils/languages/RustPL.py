import re

from .ProgrammingLanguage import ProgrammingLanguage

class RustPL(ProgrammingLanguage):
    def get_import_prefix(self):
        return "use "

    def get_snippet_separator(self):
        return "}\n\n"

    def extract_imports(self, lines):
        pattern = r'use\s+([\w:]+);'
        libraries = []
        for line in lines:
            matches = re.findall(pattern, line)
            if matches:
                library_names = [match for match in matches]
                libraries.extend(library_names)
        return libraries