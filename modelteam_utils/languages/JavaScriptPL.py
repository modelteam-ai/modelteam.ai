import re

from .ProgrammingLanguage import ProgrammingLanguage


class JavaScriptPL(ProgrammingLanguage):
    def get_import_prefix(self):
        return "import "

    def get_snippet_seperator(self):
        return "}\n\n"

    def get_code_quality(self):
        pass

    def get_code_lifetime(self):
        pass

    def extract_imports(self, lines):
        pattern = r"import\s+(\w+)\s+from\s+'([\w-]+)';"
        libraries = []
        for line in lines:
            if line.startswith("import"):
                matches = re.findall(pattern, line)
                library_names = [match[1] for match in matches]
                libraries.extend(library_names)
        return libraries
