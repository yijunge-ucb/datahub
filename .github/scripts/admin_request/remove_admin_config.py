import os
import re
from pathlib import Path


from pathlib import Path

def remove_role_from_loadroles(yaml_path: Path, course_id: str):
    role_key = f"course-staff-{course_id}:"

    with yaml_path.open("r") as f:
        lines = f.readlines()

    jupyterhub_indent = None
    hub_indent = None
    loadroles_indent = None

    loadroles_start = None
    loadroles_end = None

    # Locate jupyterhub -> hub -> loadRoles
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue  

        indent = len(line) - len(stripped)

        if stripped.startswith("jupyterhub:"):
            jupyterhub_indent = indent
            hub_indent = None
            loadroles_indent = None
            continue

        if jupyterhub_indent is not None and indent > jupyterhub_indent:
            if stripped.startswith("hub:"):
                hub_indent = indent
                loadroles_indent = None
                continue

            if hub_indent is not None and indent > hub_indent:
                if stripped.startswith("loadRoles:"):
                    loadroles_indent = indent
                    loadroles_start = i
                    continue

    if loadroles_start is None:
        print("No loadRoles section found. Nothing removed.")
        return

    # Find the end of loadRoles block
    for j in range(loadroles_start + 1, len(lines)):
        line = lines[j]
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue  
        indent = len(line) - len(stripped)

        if indent <= loadroles_indent:
            loadroles_end = j
            break
    else:
        loadroles_end = len(lines)

    role_indent = loadroles_indent + 2
    remove_start = None
    remove_end = None

    # Find the role entry and its sub-block
    i = loadroles_start + 1
    while i < loadroles_end:
        line = lines[i]
        stripped = line.lstrip()

        if not stripped or stripped.startswith("#"):
            i += 1
            continue  

        indent = len(line) - len(stripped)

        if indent == role_indent and stripped.rstrip() == role_key:
            remove_start = i
            remove_end = i + 1

            while remove_end < loadroles_end:
                next_line = lines[remove_end]
                next_stripped = next_line.lstrip()

                if not next_stripped or next_stripped.startswith("#"):
                    remove_end += 1
                    continue  #  Ignore comments inside the block too

                next_indent = len(next_line) - len(next_stripped)

                if next_indent <= role_indent:
                    break
                remove_end += 1
            break

        i += 1

    if remove_start is None:
        print(f"Role '{role_key}' not found under loadRoles. Nothing removed.")
        return

    # Remove the role lines
    del lines[remove_start:remove_end]

    # Write back the updated file
    with yaml_path.open("w") as f:
        f.writelines(lines)

    print(f"Removed role '{role_key}' from loadRoles.")



def main():
    # Get environment variables
    hub_name = os.getenv("hub_name")
    course_id = os.getenv("course_id")

    if not hub_name or not course_id:
        raise ValueError("Missing required environment variables: hub_name and course_id")

    # Path to the YAML config
    yaml_path = Path(f"deployments/{hub_name}/config/common.yaml")

    if not yaml_path.exists():
        raise FileNotFoundError(f"Config file not found: {yaml_path}")
    
    for c_id in re.split(r"[,\s:;]+", course_id):
        if c_id:  # skip empty strings
            remove_role_from_loadroles(yaml_path, c_id)

if __name__ == "__main__":
    main()