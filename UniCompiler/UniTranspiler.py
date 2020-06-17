
#%%
import sys
import re
from Parser import parse
from Writer import writeFromTree

# %%
import subprocess
def main():
    filename = "../source.go" #sys.argv[1]
    path_to_exe = compile(filename)
    return subprocess.run(f"{path_to_exe}", capture_output=True).stdout.decode()

def compile(filename):
    code = ""
    with open(filename) as f:
        raw = f.read()
        raw = re.sub(r"\n(.)*//.*\n", r'\n\1\n', raw)
        parsed = parse(raw.replace("\n", ";").replace("	", "°"))
        code = writeFromTree(parsed)
    dist = filename.replace(".go", ".cpp").replace(".uni", ".cpp")
    exe = dist.replace(".cpp", ".exe")
    with open(dist, "w") as f:
        f.write(code)
    subprocess.run(f"g++ {dist} -fconcepts -std=gnu++2a -o {exe}")
    return exe

# %%
if __name__ == "__main__":
    main()

# %%
