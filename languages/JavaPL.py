import re

from .ProgrammingLanguage import ProgrammingLanguage


class JavaPL(ProgrammingLanguage):
    def get_import_prefix(self):
        return "import "

    def extract_documentation(self, code_lines):
        javadocs = []
        inside_javadoc = False
        current_javadoc = ""

        for line in code_lines:
            line = line.strip()

            if line.startswith('/**') and line.count('*/') == 0:
                inside_javadoc = True
                current_javadoc += line[3:]
            elif inside_javadoc:
                if line.count('*/') > 0:
                    current_javadoc += '\n' + line[:-2]
                    javadocs.append(current_javadoc.strip())
                    current_javadoc = ""
                    inside_javadoc = False
                else:
                    current_javadoc += '\n' + line[2:]
            elif line.startswith('//'):
                continue

        return javadocs

    def get_snippet_seperator(self):
        return "}\n\n"

    def get_code_quality(self):
        pass

    def get_code_lifetime(self):
        pass

    def extract_imports(self, lines):
        # Find all matches in the Java code
        pattern = r"import\s+([\w.]+(?:\*|[\w*]+)?);"
        libraries = []
        import_lines = []
        for line in lines:
            if line.startswith("import"):
                import_lines.append(line)
                matches = re.findall(pattern, line)
                library_names = [match for match in matches]
                libraries.extend(library_names)
        return libraries, import_lines
