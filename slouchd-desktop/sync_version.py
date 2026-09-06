# sync version info across version_info.txt and src/__init__.py
import os
import re
import sys


def sync_version(version_str: str):
    # clean tag prefix if present
    ver = version_str.strip().lstrip("v")
    if not ver:
        ver = "0.1.0"

    # extract numbers for windows quad tuple
    nums = [int(n) for n in re.findall(r"\d+", ver)]
    while len(nums) < 4:
        nums.append(0)

    quad_tuple = f"({nums[0]}, {nums[1]}, {nums[2]}, {nums[3]})"
    quad_str = f"{nums[0]}.{nums[1]}.{nums[2]}.{nums[3]}"

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # update windows pe version resource
    version_info_path = os.path.join(base_dir, "version_info.txt")
    if os.path.exists(version_info_path):
        with open(version_info_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r"filevers=\([^)]+\)", f"filevers={quad_tuple}", content)
        content = re.sub(r"prodvers=\([^)]+\)", f"prodvers={quad_tuple}", content)
        content = re.sub(
            r"StringStruct\('FileVersion',\s*'[^']+'\)",
            f"StringStruct('FileVersion', '{quad_str}')",
            content,
        )
        content = re.sub(
            r"StringStruct\('ProductVersion',\s*'[^']+'\)",
            f"StringStruct('ProductVersion', '{quad_str}')",
            content,
        )
        with open(version_info_path, "w", encoding="utf-8") as f:
            f.write(content)

    # update package version
    init_path = os.path.join(base_dir, "src", "__init__.py")
    if os.path.exists(init_path):
        with open(init_path, "w", encoding="utf-8") as f:
            f.write(f'"""slouchd package"""\n\n__version__ = "{ver}"\n')

    # update inno setup script default version
    iss_path = os.path.join(base_dir, "installer", "slouchd.iss")
    if os.path.exists(iss_path):
        with open(iss_path, "r", encoding="utf-8") as f:
            iss_content = f.read()
        iss_content = re.sub(
            r'(#define\s+MyAppVersion\s+)"[^"]+"',
            rf'\g<1>"{ver}"',
            iss_content,
        )
        with open(iss_path, "w", encoding="utf-8") as f:
            f.write(iss_content)

    print(f"version synced to {ver} ({quad_str})")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("APP_VERSION", "0.1.0")
    sync_version(target)
