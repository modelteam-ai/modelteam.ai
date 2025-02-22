import re

from .ProgrammingLanguage import ProgrammingLanguage


class KotlinPL(ProgrammingLanguage):
    def get_import_prefix(self):
        return "import "

    def extract_imports(self, lines):
        pattern = r"^\s*import\s+([\w.]+)"
        libraries = []
        for line in lines:
            if line.startswith("import"):
                matches = re.findall(pattern, line)
                library_names = [match[1] for match in matches]
                libraries.extend(library_names)
        return libraries

    def get_snippet_separator(self):
        return "}\n\n"
