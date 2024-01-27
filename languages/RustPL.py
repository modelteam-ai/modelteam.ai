from .ProgrammingLanguage import ProgrammingLanguage


def get_libs(import_line):
    import_line = import_line.replace("use", "").replace(";", "").replace(" as ", ",").replace(" ", "")
    libs = []
    if "{" in import_line:
        parent = []
        start = -1
        for i in range(len(import_line) - 1):
            c = import_line[i]
            if c == "{":
                parent.append(import_line[start: i])
                start = -1
            elif c == "}":
                if start != -1:
                    libs.append("".join(parent) + import_line[start: i])
                    start = -1
                if len(parent) > 0:
                    parent.pop()
            elif c == ",":
                if start != -1:
                    libs.append("".join(parent) + import_line[start: i])
                    start = -1
            elif c == ' ':
                continue
            elif start == -1:
                start = i
    else:
        libs.append(import_line)
    return libs


class RustPL(ProgrammingLanguage):
    def get_code_quality(self):
        pass

    def get_code_lifetime(self):
        pass

    def extract_imports(self, lines):
        code_snippet_as_a_single_line = " ".join(lines).replace("\n", " ")
        lib_parts = code_snippet_as_a_single_line.split(";")
        libs = []
        for l in lib_parts:
            l_strip = l.strip()
            if l_strip.startswith("use"):
                libs.extend(get_libs(l_strip))
        return libs
