from backend.diagnostics.route_parser import parse_project

routes, diagnostics = parse_project("backend/sample_project")

print("\nDETECTED ROUTES:")

for route in routes:
    print(route)

print("\nDIAGNOSTICS:")

for diagnostic in diagnostics:
    print(diagnostic)