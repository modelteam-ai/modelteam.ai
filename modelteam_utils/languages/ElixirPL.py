import re

from .ProgrammingLanguage import ProgrammingLanguage


class ElixirPL(ProgrammingLanguage):
    def get_import_prefix(self):
        return "import "

    def get_snippet_separator(self):
        return "}\n\n"

    def extract_imports(self, lines):
        pattern = r"import\s+(\w+)\s+from\s+'([\w-]+)';"
        libraries = []
        for line in lines:
            if line.startswith("import"):
                matches = re.findall(pattern, line)
                library_names = [match[1] for match in matches]
                libraries.extend(library_names)
        return libraries


    def extract_documentation(self, code_lines):
        comments = []
        inside_comment = False
        current_comment = ""

        for line in code_lines:
            line = line.strip()
            if line.startswith('@moduledoc') or line.startswith('@doc'):
                inside_comment = True
            elif inside_comment:
                if line.count('"""') > 0:
                    comments.append(current_comment.strip())
                    current_comment = ""
                    inside_comment = False
                else:
                    current_comment += line + "\n"

        if inside_comment and current_comment and len(current_comment) > 300:
            comments.append(current_comment.strip())
        return comments
