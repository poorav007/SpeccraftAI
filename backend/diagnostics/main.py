
import json
import sys
from pathlib import Path

from diagnostics.route_parser import parse_project


def main():

    # Get the project folder from the terminal
    if len(sys.argv) < 2:
        print("Usage: python main.py <project_folder>")
        return

    project_folder = Path(sys.argv[1])

    if not project_folder.is_dir():
        print(f"Project folder not found: {project_folder}")
        return

    # Scan the project
    routes, diagnostics = parse_project(str(project_folder))

    # Display detected routes
    print("\n========== DETECTED API ROUTES ==========\n")

    for route in routes:
        print(
            f"{route['method']} {route['path']} "
            f"| Function: {route['function']} "
            f"| File: {route['file']} "
            f"| Line: {route['line']}"
        )

    if not routes:
        print("No API routes detected.")

    # Display diagnostics
    print("\n========== DIAGNOSTICS ==========\n")

    for diagnostic in diagnostics:
        print(json.dumps(vars(diagnostic), indent=4))

    if not diagnostics:
        print("No diagnostics found.")

    print("\n========== SUMMARY ==========")
    print(f"Total routes detected: {len(routes)}")
    print(f"Total diagnostics: {len(diagnostics)}")


if __name__ == "__main__":
    main()
