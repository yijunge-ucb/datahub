import os
import re
from pathlib import Path


def remove_group_profile(yaml_path: Path, course_id: str, course_name: str):
    with yaml_path.open("r") as f:
        lines = f.readlines()

    # Indents
    jupyterhub_indent = 0
    custom_indent = jupyterhub_indent + 2
    group_profiles_indent = custom_indent + 2
    course_indent = group_profiles_indent + 2

    course_key_prefix = f"course::{course_id}::enrollment_type::"

    jupyterhub_start = None
    custom_start = None
    group_profiles_start = None
    group_profiles_end = None

    def is_comment_or_blank(line):
        return not line.strip() or line.lstrip().startswith("#")

    # Step 1: Locate jupyterhub:
    for i, line in enumerate(lines):
        if is_comment_or_blank(line):
            continue
        if line.lstrip().startswith("jupyterhub:"):
            jupyterhub_start = i
            jupyterhub_indent = len(line) - len(line.lstrip())
            break
    if jupyterhub_start is None:
        print("No 'jupyterhub:' block found. Nothing to remove.")
        return

    # Step 2: Locate custom:
    for i in range(jupyterhub_start + 1, len(lines)):
        line = lines[i]
        if is_comment_or_blank(line):
            continue
        indent = len(line) - len(line.lstrip())
        if line.lstrip().startswith("custom:") and indent == custom_indent:
            custom_start = i
            break
        if indent <= jupyterhub_indent:
            break
    if custom_start is None:
        print("No 'custom:' block found. Nothing to remove.")
        return

    # Step 3: Locate group_profiles:
    for i in range(custom_start + 1, len(lines)):
        line = lines[i]
        if is_comment_or_blank(line):
            continue
        indent = len(line) - len(line.lstrip())
        if line.lstrip().startswith("group_profiles:") and indent == group_profiles_indent:
            group_profiles_start = i
            break
        if indent <= custom_indent:
            break
    if group_profiles_start is None:
        print("No 'group_profiles:' block found. Nothing to remove.")
        return

    # Step 4: Find end of group_profiles block
    for i in range(group_profiles_start + 1, len(lines)):
        if is_comment_or_blank(lines[i]):
            continue
        indent = len(lines[i]) - len(lines[i].lstrip())
        if indent <= group_profiles_indent:
            group_profiles_end = i
            break
    else:
        group_profiles_end = len(lines)

    # Step 5: Remove matching course blocks
    remaining_lines = []
    i = group_profiles_start + 1
    removed_any = False

    while i < group_profiles_end:
        line = lines[i]
        if is_comment_or_blank(line):
            remaining_lines.append(line)
            i += 1
            continue

        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if indent == course_indent and stripped.startswith(course_key_prefix):
            # Skip this block
            j = i + 1
            while j < group_profiles_end:
                if is_comment_or_blank(lines[j]):
                    j += 1
                    continue
                next_indent = len(lines[j]) - len(lines[j].lstrip())
                if next_indent <= course_indent:
                    break
                j += 1
            i = j
            removed_any = True
        else:
            remaining_lines.append(line)
            i += 1

    if not removed_any:
        print(f"No matching group profile entries for course::{course_id} found.")
        return

    # Step 6: Rebuild the file
    lines = lines[:group_profiles_start + 1] + remaining_lines + lines[group_profiles_end:]

    # Step 7: Check if group_profiles is now empty (ignoring comments)
    has_content = any(
        not is_comment_or_blank(line) and (len(line) - len(line.lstrip())) > group_profiles_indent
        for line in remaining_lines
    )
    if not has_content:
        del lines[group_profiles_start]  # remove group_profiles:
        print("Removed empty 'group_profiles:' section.")

        # Step 8: Check if custom is now empty (ignoring comments)
        custom_end = None
        for i in range(custom_start + 1, len(lines)):
            if is_comment_or_blank(lines[i]):
                continue
            indent = len(lines[i]) - len(lines[i].lstrip())
            if indent <= custom_indent:
                custom_end = i
                break
        else:
            custom_end = len(lines)

        custom_has_content = any(
            not is_comment_or_blank(line) and (len(line) - len(line.lstrip())) > custom_indent
            for line in lines[custom_start + 1:custom_end]
        )
        if not custom_has_content:
            del lines[custom_start]
            print("Removed empty 'custom:' section.")

    # Write back
    with yaml_path.open("w") as f:
        f.writelines(lines)

    print(f"Removed group profile for course::{course_id}")




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
            c_name = "bcourses-" + c_id.strip()
            remove_group_profile(yaml_path, c_id, c_name)


if __name__ == "__main__":
    main()



