import ast
import importlib
import importlib.machinery
import inspect
import pkgutil
import shutil
from dataclasses import dataclass, field
from pathlib import Path

PACKAGE = "core"
CORE = Path(PACKAGE).resolve()
DIST = Path("dist").resolve()


def modified_all_suffixes(orig=importlib.machinery.all_suffixes) -> list[str]:
    return orig() + [".pyi"]


importlib.machinery.all_suffixes = modified_all_suffixes
BUILTIN_NAMES = frozenset(m.name for m in pkgutil.iter_modules(["typings"])) | {"board"}


def main():
    transformer = Transformer()
    transformer.visit(ast.parse((CORE / "main.py").read_text()))
    imports = list(transformer.imports)
    shutil.copyfile(CORE / "main.py", DIST / "main.py")
    for import_ in imports:
        shutil.copyfile(import_, DIST / Path(import_).name)


@dataclass
class Transformer(ast.NodeTransformer):
    imports: dict[str, None] = field(default_factory=dict)  # set but preserve order

    def visit_Module(self, node: ast.Module):
        for import_node in node.body:
            match import_node:
                case ast.Import():
                    self.visit_Import(import_node)
                case ast.ImportFrom():
                    self.visit_ImportFrom(import_node)
                case _:
                    pass

    def visit_Import(self, node: ast.Import):
        for module_node in node.names:
            if module_node.name in BUILTIN_NAMES or module_node.name in self.imports:
                continue
            module = importlib.import_module(module_node.name, PACKAGE)
            assert module.__file__ is not None
            self.imports[module.__file__] = None
            module_ast = ast.parse(inspect.getsource(module))
            self.visit(module_ast)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        assert node.module is not None
        if node.module in BUILTIN_NAMES or node.module in self.imports:
            return
        print(ast.dump(node))
        module = importlib.import_module(node.module, PACKAGE)
        print("got mod", module)
        module_ast = ast.parse(inspect.getsource(module))
        self.visit(module_ast)


if __name__ == "__main__":
    main()
