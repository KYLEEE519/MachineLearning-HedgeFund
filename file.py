import os

def print_repo_structure(root_dir="."):
    for dirpath, dirnames, filenames in os.walk(root_dir):
        level = dirpath.replace(root_dir, "").count(os.sep)
        indent = " " * (level * 4)
        print(f"{indent}📂 {os.path.basename(dirpath)}/")
        sub_indent = " " * ((level + 1) * 4)
        for filename in filenames:
            print(f"{sub_indent}📄 {filename}")

print_repo_structure(".")  # 当前目录
