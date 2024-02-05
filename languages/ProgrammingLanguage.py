# Abstract class for programming languages
from abc import ABC, abstractmethod

from modelteam.utils.utils import load_public_libraries


class ProgrammingLanguage(ABC):
    def __init__(self, extension, snippet, file_name):
        self.extension = extension
        self.public_libraries = None
        self.snippet = snippet
        self.file_name = file_name

    @abstractmethod
    def get_import_prefix(self):
        pass

    def get_library_names(self, include_all_libraries=False):
        if include_all_libraries:
            lib_list = self.extract_imports(self.get_code_from_file(self.file_name))
        else:
            lib_list = self.extract_imports(self.get_newly_added_lines(self.snippet))
        return lib_list

    def filter_non_public_libraries(self, libraries):
        if not self.public_libraries:
            self.public_libraries = load_public_libraries("config/libraries")
        return [library for library in libraries if library in self.public_libraries[self.extension]]

    def get_name(self):
        return self.extension

    @abstractmethod
    def extract_imports(self, lines):
        pass

    def extract_documentation(self, code_lines):
        comments = []
        inside_comment = False
        current_comment = ""

        for line in code_lines:
            line = line.strip()
            if line.startswith('/*') and line.count('*/') == 0:
                inside_comment = True
                current_comment += line[2:]
            elif inside_comment:
                if line.count('*/') > 0:
                    current_comment += '\n' + line[:-2]
                    comments.append(current_comment.strip())
                    current_comment = ""
                    inside_comment = False
                else:
                    if line.startswith('*'):
                        line = line[1:]
                    current_comment += '\n' + line

        return comments

    @abstractmethod
    def get_code_quality(self):
        pass

    @abstractmethod
    def get_code_lifetime(self):
        pass

    @abstractmethod
    def get_snippet_seperator(self):
        pass

    @staticmethod
    def get_newly_added_lines(snippet):
        lines = snippet.split("\n")
        filtered_lines = [line for line in lines if line.startswith('+')]
        # remove + at the beginning of the line
        filtered_lines = [line[1:] for line in filtered_lines]
        return filtered_lines

    @staticmethod
    def get_code_from_file(file_name):
        with open(file_name, "r") as f:
            try:
                lines = f.readlines()
            except UnicodeDecodeError:
                return []
        return lines
