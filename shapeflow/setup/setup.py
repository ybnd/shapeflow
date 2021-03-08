from sys import executable
from subprocess import check_call

print("\nSetting up shapeflow...\n")

check_call([executable, "sf.py", "setup-cairo", "--cleanup"])
check_call([executable, "sf.py", "get-compiled-ui", "--replace"])
check_call([executable, "sf.py", "declutter"])

print("\n\nAll done.")