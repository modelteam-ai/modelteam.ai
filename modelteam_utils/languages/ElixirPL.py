import re

from .ProgrammingLanguage import ProgrammingLanguage


class ElixirPL(ProgrammingLanguage):
    def get_import_prefix(self):
        return "import "

    def get_snippet_seperator(self):
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

        # Regular expressions for Elixir docstrings
        moduledoc_pattern = r'@moduledoc\s+"(.*?)"'
        doc_pattern = r'@doc\s+"(.*?)"\s*def\s+(\w+)\s*\('

        # Join all code lines into a single string for processing
        code = "\n".join(code_lines)

        # Extract module-level documentation
        moduledoc_match = re.search(moduledoc_pattern, code, re.DOTALL)
        if moduledoc_match:
            comments.append(moduledoc_match.group(1).strip())

        # Extract function-level documentation
        doc_matches = re.findall(doc_pattern, code, re.DOTALL)
        for doc, _ in doc_matches:
            comments.append(doc.strip())

        return comments
