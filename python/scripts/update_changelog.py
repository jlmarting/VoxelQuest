"""
Actualiza CHANGELOG.md con los commits desde la última entrada documentada.

Uso:
    python3 scripts/update_changelog.py

Lee el changelog existente, encuentra el último SHA/versión referenciado,
ejecuta `git log` desde ese punto hasta HEAD, clasifica los commits por
prefijo Conventional Commit y los escribe bajo [Unreleased].
"""

import re, subprocess, sys
from datetime import date

CHANGELOG = "CHANGELOG.md"

# mapping conventional commit type -> changelog category
CATEGORY = {
    "feat": "Added",
    "feature": "Added",
    "add": "Added",
    "added": "Added",
    "fix": "Fixed",
    "bugfix": "Fixed",
    "bug": "Fixed",
    "hotfix": "Fixed",
    "change": "Changed",
    "changed": "Changed",
    "refactor": "Changed",
    "refact": "Changed",
    "improve": "Changed",
    "perf": "Changed",
    "enhance": "Changed",
    "docs": "Changed",
    "doc": "Changed",
    "style": "Changed",
    "deprecate": "Deprecated",
    "deprecated": "Deprecated",
    "remove": "Removed",
    "removed": "Removed",
    "delete": "Removed",
    "security": "Security",
    "chore": "Changed",
    "test": "Changed",
    "tests": "Changed",
    "ci": "Changed",
}


def last_ref_in_changelog():
    """Busca la ultima referencia (SHA corto o version) en CHANGELOG.md."""
    try:
        with open(CHANGELOG, encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return None

    # cabeceras tipo ## [<ref>] o ## [<ref>] — <date>
    matches = re.findall(r"^## \[([a-f0-9]{7,40}|v?\d[\w.]*)\]", content, re.MULTILINE)
    if matches:
        # el primero es Unreleased, el segundo es la ultima version documentada
        if len(matches) > 1:
            return matches[1]
        return matches[0]
    return None


def git_log_since(ref):
    """Devuelve lista de (hash, mensaje) desde ref hasta HEAD."""
    if ref is None:
        cmd = ["git", "log", "--oneline", "--no-decorate", "HEAD"]
    else:
        cmd = ["git", "log", "--oneline", "--no-decorate", f"{ref}..HEAD"]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
    except subprocess.CalledProcessError:
        return []
    if not out:
        return []
    lines = out.split("\n")
    result = []
    for line in lines:
        parts = line.strip().split(" ", 1)
        if len(parts) == 2:
            result.append((parts[0], parts[1]))
    return result


def classify(message):
    """Devuelve (categoria, texto_sin_prefijo)."""
    # feat(scope): msg  o  feat: msg
    m = re.match(r"^(\w+)(?:\([^)]*\))?:\s*(.*)", message)
    if m:
        prefix = m.group(1).lower().strip()
        rest = m.group(2).strip()
        cat = CATEGORY.get(prefix, "Changed")
        return cat, rest
    # si no tiene prefijo conventional, intenta inferir
    lower = message.lower()
    if lower.startswith("add") or lower.startswith("new") or lower.startswith("creat"):
        return "Added", message
    if (
        lower.startswith("fix")
        or lower.startswith("correct")
        or lower.startswith("patch")
    ):
        return "Fixed", message
    return "Changed", message


def update_changelog(entries):
    """Inserta o actualiza entradas bajo [Unreleased] y devuelve el nuevo contenido."""
    try:
        with open(CHANGELOG, encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = "# Changelog\n\n"

    # agrupar por categoria manteniendo orden de primera aparicion
    categories = {}
    for cat, text in entries:
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(text)

    ordered_cats = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
    unreleased_lines = ["## [Unreleased]", ""]
    for cat in ordered_cats:
        items = categories.get(cat)
        if not items:
            continue
        unreleased_lines.append(f"### {cat}")
        for item in items:
            unreleased_lines.append(f"- {item}")
        unreleased_lines.append("")

    unreleased_block = "\n".join(unreleased_lines).strip() + "\n\n"

    # si ya hay [Unreleased], reemplazar el bloque
    pattern = r"## \[Unreleased\].*?(?=\n## \[|\Z)"
    new_content = re.sub(
        pattern, unreleased_block.strip(), content, count=1, flags=re.DOTALL
    )
    if new_content == content:
        # no habia [Unreleased] -> insertar al inicio
        after_header = re.search(r"^# .*?\n\n?", content)
        if after_header:
            pos = after_header.end()
            new_content = content[:pos] + "\n" + unreleased_block + content[pos:]
        else:
            new_content = content + "\n" + unreleased_block

    with open(CHANGELOG, "w", encoding="utf-8") as f:
        f.write(new_content)
    return "OK"


if __name__ == "__main__":
    last = last_ref_in_changelog()
    if last:
        print(f"Ultima referencia en changelog: {last}")
    else:
        print("No se encontro referencia previa — se usara todo el log")

    commits = git_log_since(last)
    if not commits:
        print("No hay commits nuevos desde la ultima referencia.")
        sys.exit(0)

    entries = []
    for h, msg in commits:
        cat, text = classify(msg)
        entries.append((cat, text))
        print(f"  {h}  [{cat}] {text[:70]}")

    update_changelog(entries)
    print(f"\n{len(entries)} commits anadidos a [Unreleased] en CHANGELOG.md")
