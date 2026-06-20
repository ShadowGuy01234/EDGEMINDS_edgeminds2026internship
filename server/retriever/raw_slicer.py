import os

def get_raw_source_slice(file_path: str, start_line: int, end_line: int) -> str:
    """
    Reads the file at file_path and returns the exact lines from start_line to end_line (1-indexed).
    If the slice has more than 300 lines, truncates the slice to 300 lines and appends
    a '// ...truncated...' marker at the end.
    """
    if not os.path.exists(file_path):
        return f"Error: File '{file_path}' not found on disk."

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        return f"Error reading file '{file_path}': {str(e)}"

    # start_line and end_line are 1-indexed
    start = (start_line - 1) if start_line is not None else 0
    end = end_line if end_line is not None else len(lines)

    # Bound range safely
    start = max(0, min(start, len(lines)))
    end = max(start, min(end, len(lines)))

    sliced_lines = lines[start:end]

    if len(sliced_lines) > 300:
        sliced_lines = sliced_lines[:300]
        # Add a newline if last line doesn't end with one
        if sliced_lines and not sliced_lines[-1].endswith("\n"):
            sliced_lines[-1] = sliced_lines[-1] + "\n"
        sliced_lines.append("// ...truncated...\n")

    return "".join(sliced_lines)
