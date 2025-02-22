import re

from .ProgrammingLanguage import ProgrammingLanguage


class RubyPL(ProgrammingLanguage):
    def extract_documentation(self, code_lines):
        comments = []
        inside_comment = False
        current_comment = ""

        for line in code_lines:
            line = line.strip()

            if line.startswith('=begin') and not line.endswith('=end'):
                inside_comment = True
                current_comment += line[6:]
            elif inside_comment:
                if line.startswith('=end'):
                    current_comment += '\n' + line[4:]
                    comments.append(current_comment.strip())
                    current_comment = ""
                    inside_comment = False
                else:
                    current_comment += '\n' + line

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
