import os
import re
from pathlib import Path


from pathlib import Path

def insert_role(yaml_path: Path, course_id: str, issue_number: str, end_date: str, course_name: str):
    role_key = f"course-staff-{course_id}:"

    with yaml_path.open("r") as f:
        lines = f.readlines()

    if lines and not lines[-1].endswith('\n'):
        lines[-1] += '\n'

    jupyterhub_indent = None
    hub_indent = None
    loadroles_indent = None

    jupyterhub_start = None
    hub_start = None
    loadroles_start = None

    # First pass: Find the sections and their indentations, skipping comments
    for i, line in enumerate(lines):
        stripped = line.lstrip()

        if not stripped or stripped.startswith("#"):
            continue  # Skip comments or empty lines

        indent = len(line) - len(stripped)

        if stripped.startswith("jupyterhub:"):
            jupyterhub_indent = indent
            jupyterhub_start = i
            hub_indent = None
            loadroles_indent = None
            continue

        if jupyterhub_indent is not None and indent > jupyterhub_indent:
            if stripped.startswith("hub:"):
                hub_indent = indent
                hub_start = i
                loadroles_indent = None
                continue

            if hub_indent is not None and indent > hub_indent:
                if stripped.startswith("loadRoles:"):
                    loadroles_indent = indent
                    loadroles_start = i
                    continue

    # If loadRoles doesn't exist, insert it
    if loadroles_start is None:
        if hub_start is None:
            raise ValueError("Could not find the jupyterhub -> hub section.")

        # Insert loadRoles block after the hub: line
        loadroles_indent = hub_indent + 2
        loadroles_start = hub_start + 1
        lines.insert(loadroles_start, " " * loadroles_indent + "loadRoles:\n")

    # Find the last line of the loadRoles block (ignoring comments)
    insert_pos = loadroles_start + 1
    for j in range(loadroles_start + 1, len(lines)):
        line = lines[j]
        stripped = line.lstrip()

        if not stripped or stripped.startswith("#"):
            continue  # Skip comments or blank lines

        indent = len(line) - len(stripped)

        if indent <= loadroles_indent:
            break
        insert_pos = j + 1

    # Check if role already exists in the loadRoles block
    for k in range(loadroles_start + 1, insert_pos):
        stripped = lines[k].strip()
        if not stripped or stripped.startswith("#"):
            continue  # Skip comments

        if stripped == role_key:
            print(f"Role '{role_key}' already exists. Skipping insertion.")
            return

    # Prepare role block lines
    entry_indent = loadroles_indent + 2
    subentry_indent = entry_indent + 2

    role_block = [
        " " * entry_indent + f"{role_key}\n",
        " " * subentry_indent + f"## Course: {course_name} Bcourses ID: {course_id} End Date: {end_date} \n",
        " " * subentry_indent + f"## See issue https://github.com/berkeley-dsep-infra/datahub/issues/{issue_number} for more details.\n",
        " " * subentry_indent + "description: Enable course staff to view and access servers.\n",
        " " * subentry_indent + "scopes:\n",
        " " * (subentry_indent + 2) + "- admin-ui\n",
        " " * (subentry_indent + 2) + f"- list:users!group=course::{course_id}\n",
        " " * (subentry_indent + 2) + f"- admin:servers!group=course::{course_id}\n",
        " " * (subentry_indent + 2) + f"- access:servers!group=course::{course_id}\n",
        " " * subentry_indent + "groups:\n",
        " " * (subentry_indent + 2) + f"- course::{course_id}::enrollment_type::teacher\n",
        " " * (subentry_indent + 2) + f"- course::{course_id}::enrollment_type::ta\n",
    ]

    # Insert the new role at the end of the loadRoles block
    lines = lines[:insert_pos] + role_block + lines[insert_pos:]

    with yaml_path.open("w") as f:
        f.writelines(lines)

    print(f"Inserted role '{role_key}' at the end of loadRoles block (line {insert_pos}).")



def main():
    # Get environment variables
    hub_name = os.getenv("hub_name")
    course_id = os.getenv("course_id")
    issue_number = os.getenv("ISSUE_NUMBER")
    end_date = os.getenv("end_date").strip()
    course_name = os.getenv("course_name").strip()

    if not hub_name or not course_id or not issue_number or not course_name or not end_date:
        raise ValueError("Missing required environment variables: hub_name, course_id, ISSUE_NUMBER, course_name, or end_date")

    # Path to the YAML config
    yaml_path = Path(f"deployments/{hub_name}/config/common.yaml")

    if not yaml_path.exists():
        raise FileNotFoundError(f"Config file not found: {yaml_path}")
    
    for c_id in re.split(r"[,\s:;]+", course_id):
        if c_id:  # skip empty strings
            insert_role(yaml_path, c_id, issue_number, end_date, course_name)

if __name__ == "__main__":
    main()