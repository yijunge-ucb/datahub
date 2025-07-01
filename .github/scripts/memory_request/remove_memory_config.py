import os
import re
from pathlib import Path



def remove_group_profile(yaml_path: Path, course_id: str):
    with yaml_path.open("r") as f:
        lines = f.readlines()

    course_key = f"course::{course_id}:"

    jupyterhub_indent = None
    jupyterhub_start = None
    jupyterhub_end = None
    custom_start = None
    custom_end = None
    group_profiles_start = None
    group_profiles_end = None

    # Step 1: Locate jupyterhub:
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("jupyterhub:"):
            jupyterhub_indent = len(line) - len(stripped)
            jupyterhub_start = i
            break

    if jupyterhub_start is None:
        print("No 'jupyterhub:' block found.")
        return

    for i in range(jupyterhub_start + 1, len(lines)):
        stripped = lines[i].lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(lines[i]) - len(stripped)
        if indent <= jupyterhub_indent:
            jupyterhub_end = i
            break
    else:
        jupyterhub_end = len(lines)

    # Step 2: Find 'custom:' under jupyterhub:
    custom_indent = jupyterhub_indent + 2
    for i in range(jupyterhub_start + 1, jupyterhub_end):
        stripped = lines[i].lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("custom:"):
            custom_start = i
            break

    if custom_start is None:
        print("No 'custom:' block found under 'jupyterhub:'")
        return

    for i in range(custom_start + 1, jupyterhub_end):
        stripped = lines[i].lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(lines[i]) - len(stripped)
        if indent <= custom_indent:
            custom_end = i
            break
    else:
        custom_end = jupyterhub_end

    # Step 3: Find group_profiles:
    group_profiles_indent = custom_indent + 2
    for i in range(custom_start + 1, custom_end):
        stripped = lines[i].lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("group_profiles:"):
            group_profiles_start = i
            break

    if group_profiles_start is None:
        print("No 'group_profiles:' block found under 'custom:'")
        return

    for i in range(group_profiles_start + 1, custom_end):
        stripped = lines[i].lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(lines[i]) - len(stripped)
        if indent <= group_profiles_indent:
            group_profiles_end = i
            break
    else:
        group_profiles_end = custom_end

    # Step 4: Find course block
    group_indent = group_profiles_indent + 2
    found_course_start = None
    found_course_end = None

    for i in range(group_profiles_start + 1, group_profiles_end):
        stripped = lines[i].lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.rstrip() == course_key:
            found_course_start = i
            j = i + 1
            while j < group_profiles_end:
                sub_stripped = lines[j].lstrip()
                if not sub_stripped or sub_stripped.startswith("#"):
                    j += 1
                    continue
                if (len(lines[j]) - len(sub_stripped)) <= group_indent:
                    break
                j += 1
            found_course_end = j
            break

    if found_course_start is None:
        print(f"No block found for course::{course_id}")
        return

    # Step 5: Decide what to remove
    mem_lines = []
    other_lines_exist = False
    for i in range(found_course_start + 1, found_course_end):
        line_stripped = lines[i].lstrip()
        if not line_stripped or line_stripped.startswith("#"):
            continue
        if line_stripped.startswith("mem_limit:") or line_stripped.startswith("mem_guarantee:"):
            mem_lines.append(i)
        else:
            other_lines_exist = True

    if not other_lines_exist:
        # Remove the entire course block
        lines = lines[:found_course_start] + lines[found_course_end:]
        group_profiles_end -= (found_course_end - found_course_start)
        print(f"Removed entire group profile block for course::{course_id}")
    else:
        # Just remove mem_limit and mem_guarantee
        lines = (
            lines[:found_course_start + 1] +
            [lines[i] for i in range(found_course_start + 1, found_course_end)
             if not lines[i].lstrip().startswith("mem_limit:")
             and not lines[i].lstrip().startswith("mem_guarantee:")] +
            lines[found_course_end:]
        )
        group_profiles_end -= len(mem_lines)
        print(f"Removed 'mem_limit' and 'mem_guarantee' from course::{course_id} group profile")

    # Step 6: Check if group_profiles block is now empty
    def is_block_empty(start, end, min_indent):
        for i in range(start + 1, min(end, len(lines))):
            stripped = lines[i].lstrip()
            indent = len(lines[i]) - len(stripped)
            if stripped and indent > min_indent and not stripped.startswith("#"):
                return False
            if stripped and indent <= min_indent:
                break
        return True

    if is_block_empty(group_profiles_start, group_profiles_end, group_profiles_indent):
        print("Removed empty 'group_profiles:' block")
        lines = lines[:group_profiles_start] + lines[group_profiles_end:]
        custom_end -= (group_profiles_end - group_profiles_start)

    # Step 7: Check if custom block is now empty
    if is_block_empty(custom_start, custom_end, custom_indent):
        print("Removed empty 'custom:' block")
        lines = lines[:custom_start] + lines[custom_end:]

    # Final write
    with yaml_path.open("w") as f:
        f.writelines(lines)





def main():
    # Get environment variables
    hub_name = os.getenv("hub_name")
    course_id = os.getenv("course_id")

    if not hub_name or not course_id:
        raise ValueError("Missing required environment variables: hub_name, course_id")

    # Path to the YAML config
    yaml_path = Path(f"deployments/{hub_name}/config/common.yaml")

    if not yaml_path.exists():
        raise FileNotFoundError(f"Config file not found: {yaml_path}")
    
    for c_id in re.split(r"[,\s:;]+", course_id):
        if c_id:  # skip empty strings
            remove_group_profile(yaml_path, c_id)


if __name__ == "__main__":
    main()



