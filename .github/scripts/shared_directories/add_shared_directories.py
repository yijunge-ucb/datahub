import os
import re
from pathlib import Path
from datetime import datetime


def convert_date_to_semester():
    """
    The function uses the current date to determine the semester.
    It returns a string in the format "YYYY-{spring/summer/fall}" representing the semester.
    """

    now = datetime.now()
    year = now.year
    month = now.month

    if 1 <= month <= 4 or month == 12:
        semester = "spring"
    elif 5 <= month <= 7:
        semester = "summer"
    elif 8 <= month <= 11:
        semester = "fall"
    else:
        semester = "unknown"
    return f"{year}-{semester}"
   

def insert_or_update_group_profile(yaml_path: Path, course_id: str, course_name: str, end_date: str, issue_number: str):
    with yaml_path.open("r") as f:
        lines = f.readlines()
    
    if lines and not lines[-1].endswith('\n'):
        lines[-1] += '\n'

    semester = convert_date_to_semester()
    course_key_prefix = f"course::{course_id}::enrollment_type::"

    # Indentation levels
    jupyterhub_indent = 0
    custom_indent = jupyterhub_indent + 2
    group_profiles_indent = custom_indent + 2

    # Block positions
    jupyterhub_start = None
    jupyterhub_end = None
    custom_start = None
    group_profiles_start = None

    def is_comment_or_blank(line):
        return not line.strip() or line.lstrip().startswith("#")

    # Step 1: Locate jupyterhub
    for i, line in enumerate(lines):
        if is_comment_or_blank(line):
            continue
        if line.lstrip().startswith("jupyterhub:"):
            jupyterhub_start = i
            jupyterhub_indent = len(line) - len(line.lstrip())
            break

    if jupyterhub_start is None:
        # Add jupyterhub: at EOF
        lines.append("jupyterhub:\n")
        jupyterhub_start = len(lines) - 1
        lines.append(" " * custom_indent + "custom:\n")
        custom_start = len(lines) - 1
        lines.append(" " * group_profiles_indent + "group_profiles:\n")
        group_profiles_start = len(lines) - 1
    else:
        # Step 2: Find end of jupyterhub block
        for i in range(jupyterhub_start + 1, len(lines)):
            if is_comment_or_blank(lines[i]):
                continue
            indent = len(lines[i]) - len(lines[i].lstrip())
            if indent <= jupyterhub_indent:
                jupyterhub_end = i
                break
        else:
            jupyterhub_end = len(lines)

        # Step 3: Find or insert custom:
        for i in range(jupyterhub_start + 1, jupyterhub_end):
            if is_comment_or_blank(lines[i]):
                continue
            if lines[i].lstrip().startswith("custom:") and \
               len(lines[i]) - len(lines[i].lstrip()) == custom_indent:
                custom_start = i
                break

        if custom_start is None:
            custom_start = jupyterhub_end
            lines.insert(jupyterhub_end, " " * custom_indent + "custom:\n")
            jupyterhub_end += 1

        # Step 4: Find or insert group_profiles:
        for i in range(custom_start + 1, jupyterhub_end):
            if is_comment_or_blank(lines[i]):
                continue
            if lines[i].lstrip().startswith("group_profiles:") and \
               len(lines[i]) - len(lines[i].lstrip()) == group_profiles_indent:
                group_profiles_start = i
                break

        if group_profiles_start is None:
            group_profiles_start = jupyterhub_end
            lines.insert(jupyterhub_end, " " * group_profiles_indent + "group_profiles:\n")
            jupyterhub_end += 1

    # Step 5: Remove old course block
    group_profiles_end = None
    for i in range(group_profiles_start + 1, len(lines)):
        if is_comment_or_blank(lines[i]):
            continue
        indent = len(lines[i]) - len(lines[i].lstrip())
        if indent <= group_profiles_indent:
            group_profiles_end = i
            break
    else:
        group_profiles_end = len(lines)

    # Remove existing course block
    new_group_lines = []
    i = group_profiles_start + 1
    while i < group_profiles_end:
        line = lines[i]
        if is_comment_or_blank(line):
            new_group_lines.append(line)
            i += 1
            continue

        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if indent == group_profiles_indent + 2 and stripped.startswith(course_key_prefix):
            j = i + 1
            while j < group_profiles_end:
                if is_comment_or_blank(lines[j]):
                    j += 1
                    continue
                next_indent = len(lines[j]) - len(lines[j].lstrip())
                if next_indent <= group_profiles_indent + 2:
                    break
                j += 1
            i = j  # skip this course block
        else:
            new_group_lines.append(lines[i])
            i += 1

    lines = lines[:group_profiles_start + 1] + new_group_lines + lines[group_profiles_end:]
    group_profiles_end = group_profiles_start + 1 + len(new_group_lines)

    # Step 6: Build new block
    def make_block(role: str, readonly: bool):
        ei = group_profiles_indent + 2
        si = ei + 2
        ssi = si + 2
        access = "readonly" if readonly else "readwrite"
        return [
            " " * ei + f"course::{course_id}::enrollment_type::{role}:\n",
            " " * ei + f"## Course Name: {course_name} Bcourses ID: {course_id} End Date: {end_date}\n",
            " " * ei + f"## See issue https://github.com/berkeley-dsep-infra/datahub/issues/{issue_number} for details.\n",
            " " * si + "extraVolumeMounts:\n",
            " " * ssi + "- name: home\n",
            " " * (ssi + 2) + f"mountPath: /home/jovyan/_shared/{course_name}-{access}\n",
            " " * (ssi + 2) + f"subPath: _shared/{semester}/courses/{course_id}\n",
            " " * (ssi + 2) + f"readOnly: {'true' if readonly else 'false'}\n"
        ]

    new_block = (
        make_block("teacher", False) +
        make_block("ta", False) +
        make_block("observer", True) +
        make_block("student", True)
    )

    # Step 7: Append new block at end of group_profiles
    lines = lines[:group_profiles_end] + new_block + lines[group_profiles_end:]

    # Write back
    with yaml_path.open("w") as f:
        f.writelines(lines)

    print(f"Inserted or updated group profile for course::{course_id}")



def main():
    # Get environment variables
    hub_name = os.getenv("hub_name")
    course_id = os.getenv("course_id")
    issue_number = os.getenv("ISSUE_NUMBER")
    end_date = os.getenv("end_date").strip()
    course_name = os.getenv("course_name").strip()
 

    if not hub_name or not course_id or not issue_number or not end_date or not course_name:
        raise ValueError("Missing required environment variables: hub_name, course_id, ISSUE_NUMBER, end_date, or course_name")

    # Path to the YAML config
    yaml_path = Path(f"deployments/{hub_name}/config/common.yaml")

    if not yaml_path.exists():
        raise FileNotFoundError(f"Config file not found: {yaml_path}")
    
    for c_id in re.split(r"[,\s:;]+", course_id):
        if c_id:  # skip empty strings
            c_name = "bcourses-" + c_id.strip()
            insert_or_update_group_profile(yaml_path, c_id, c_name, end_date, issue_number)
            


if __name__ == "__main__":
    main()



