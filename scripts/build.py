import shutil
import subprocess


def main():
    shutil.copytree("core", "dist/core", ignore=lambda _, __: {"__pycache__", "main.py"}, dirs_exist_ok=True)
    subprocess.run(["pyminify", "dist/core/", "--in-place", "--remove-literal-statements", "--remove-asserts"])


if __name__ == "__main__":
    main()
