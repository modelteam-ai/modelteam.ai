import re

from .ProgrammingLanguage import ProgrammingLanguage


class CppPL(ProgrammingLanguage):
    def get_import_prefix(self):
        return "#include "

    def get_snippet_seperator(self):
        return "}\n\n"

    def get_code_quality(self):
        pass

    def get_code_lifetime(self):
        pass

    def extract_imports(self, lines):
        pattern = r'#include\s+[<"]([^<"]+)[>"]'
        libraries = []
        import_lines = []
        for line in lines:
            matches = re.findall(pattern, line)
            if matches:
                import_lines.append(line)
                library_names = [match for match in matches]
                libraries.extend(library_names)
        return libraries, import_lines
