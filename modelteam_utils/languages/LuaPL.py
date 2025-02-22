import re

from .ProgrammingLanguage import ProgrammingLanguage

class LuaPL(ProgrammingLanguage):
    def extract_documentation(self, code_lines):
        comments = []
        inside_comment = False
        current_comment = ""

        for line in code_lines:
            line = line.strip()

            # Check for the start of a multi-line comment
            if line.startswith("--[["):
                inside_comment = True
                current_comment += line[4:]
            elif inside_comment:
                if line.endswith("]]"):
                    inside_comment = False
                    current_comment += '\n' + line[:-2]  # Capture text before "]]"
                    comments.append(current_comment.strip())
                    current_comment = ""
                else:
                    current_comment += '\n' + line
            # Capture single-line comments
            elif line.startswith("--"):
                current_comment += '\n' + line[2:]
            else:
                if current_comment and len(current_comment) > 300:
                    comments.append(current_comment.strip())
                    current_comment = ""

        # Append any trailing multi-line comment that wasn't closed
        if inside_comment and current_comment and len(current_comment) > 300:
            comments.append(current_comment.strip())

        return comments

    def get_import_prefix(self):
        return "require "

    def get_snippet_separator(self):
        return "end\n\n"

    def extract_imports(self, lines):
        pattern = r'require\s+[\'"]([\w-]+)[\'"]'
        libraries = []
        for line in lines:
            matches = re.findall(pattern, line)
            if matches:
                library_names = [match for match in matches]
                libraries.extend(library_names)
        return libraries