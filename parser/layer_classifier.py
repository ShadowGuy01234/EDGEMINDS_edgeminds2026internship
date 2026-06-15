LAYER_RULES = [
    # Backend indicators
    (["api/", "routes/", "controllers/", "middleware/",
      "services/", "models/", "db/", "database/",
      "backend/", "server/", "core/"], "backend"),

    # Frontend indicators  
    (["components/", "pages/", "views/", "hooks/",
      "frontend/", "src/app/", "src/ui/", "src/pages/",
      "public/", "assets/", "styles/"], "frontend"),

    # Shared / ambiguous
    (["utils/", "helpers/", "shared/", "common/",
      "types/", "constants/", "config/"], "shared"),

    # Tests
    (["tests/", "__tests__/", "test/", "spec/"], "test"),
]

def classify_layer(file_path: str) -> str:
    path_lower = file_path.lower().replace('\\', '/')
    for patterns, layer in LAYER_RULES:
        if any(p in path_lower for p in patterns):
            return layer
    # Fallback: extension-based guess
    if file_path.endswith(".py"):
        return "backend"
    if file_path.endswith((".tsx", ".jsx")):
        return "frontend"
    if file_path.endswith(".ts") and "/api/" not in path_lower:
        return "frontend"
    return "unknown"
