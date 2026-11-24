#!/usr/bin/env python3
"""Generate aggregate language statistics; never write repository names or code."""
import json
import os
from collections import Counter
from hashlib import sha256
from html import escape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

OWNER = "MattEnmen"
API = "https://api.github.com"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "languages.svg"
COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "HTML": "#e34c26", "CSS": "#563d7c", "PHP": "#4F5D95",
    "Rust": "#dea584", "QML": "#44a51c", "Shell": "#89e051",
    "C": "#555555", "C++": "#f34b7d", "C#": "#178600",
    "Java": "#b07219", "Kotlin": "#A97BFF", "Go": "#00ADD8",
    "Lua": "#000080", "Dockerfile": "#384d54", "PowerShell": "#012456",
    "Ruby": "#701516", "SQL": "#e38c00", "Makefile": "#427819",
    "Swift": "#F05138", "Dart": "#00B4AB", "Nix": "#7e7eff",
    "Vim Script": "#199f4b", "SCSS": "#c6538c", "Vue": "#41b883",
    "Svelte": "#ff3e00", "Astro": "#ff5a03", "KDL": "#ffb787",
}
PALETTE = ["#79c0ff", "#d2a8ff", "#ffa657", "#56d364", "#ff7b72", "#a5d6ff"]


def api_get(path, token):
    request = Request(API + path, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "profile-language-stats",
    })
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        raise SystemExit(f"GitHub API: HTTP {exc.code}. Revisa el token y sus permisos.") from None
    except (URLError, TimeoutError):
        raise SystemExit("No se pudo conectar con GitHub API.") from None


def collect_languages(token):
    totals = Counter()
    page = 1
    while True:
        params = urlencode({"affiliation": "owner", "visibility": "all", "per_page": 100, "page": page})
        repos = api_get(f"/user/repos?{params}", token)
        for repo in repos:
            if repo["owner"]["login"].lower() != OWNER.lower():
                continue
            # Exclude forks and this profile repo to avoid counting the generator itself.
            if repo["fork"] or repo["name"].lower() == OWNER.lower():
                continue
            name = quote(repo["name"], safe="")
            data = api_get(f"/repos/{OWNER}/{name}/languages", token)
            totals.update({lang: size for lang, size in data.items() if size > 0})
        if len(repos) < 100:
            return totals
        page += 1


def color_for(lang):
    return COLORS.get(lang, PALETTE[int(sha256(lang.encode()).hexdigest(), 16) % len(PALETTE)])


def render(totals):
    items = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    total = sum(totals.values())
    if not total:
        raise SystemExit("No se detectaron lenguajes; se conserva la tarjeta anterior.")
    width = 600
    bar_width = width - 48
    rows = (len(items) + 1) // 2
    height = 96 + rows * 30 + 20
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Lenguajes utilizados en mis proyectos">',
        '<title>Lenguajes utilizados en mis proyectos</title>',
        f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="12" fill="#0d1117" stroke="#30363d"/>',
        '<g font-family="Verdana, DejaVu Sans, sans-serif">',
        '<text x="24" y="34" font-size="19" font-weight="bold" fill="#e6edf3">Lenguajes utilizados</text>',
        '<defs><clipPath id="bar"><rect x="24" y="52" width="552" height="12" rx="6"/></clipPath></defs>',
        '<g clip-path="url(#bar)">',
    ]
    cumulative = 0
    for lang, size in items:
        start = 24 + bar_width * cumulative / total
        cumulative += size
        end = 24 + bar_width * cumulative / total
        parts.append(f'<rect x="{start:.4f}" y="52" width="{end-start:.4f}" height="12" fill="{color_for(lang)}"/>')
    parts.append('</g>')
    for i, (lang, size) in enumerate(items):
        col, row = i % 2, i // 2
        x, y = 24 + col * 284, 91 + row * 30
        pct = 100 * size / total
        percentage = '<0.01%' if pct < 0.01 else f'{pct:.2f}%'
        label = escape(lang if len(lang) <= 25 else lang[:24] + '…')
        parts.extend([
            f'<circle cx="{x+6}" cy="{y-4}" r="5" fill="{color_for(lang)}"/>',
            f'<text x="{x+18}" y="{y}" font-size="12" fill="#e6edf3"><title>{escape(lang)}</title>{label}</text>',
            f'<text x="{x+260}" y="{y}" text-anchor="end" font-size="12" fill="#b1bac4">{escape(percentage)}</text>',
        ])
    parts.append('</g></svg>')
    return '\n'.join(parts) + '\n'


def main():
    token = os.environ.get("LANGUAGES_TOKEN")
    if not token:
        raise SystemExit("Falta el secreto LANGUAGES_TOKEN.")
    svg = render(collect_languages(token))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg, encoding="utf-8")
    print("Tarjeta de lenguajes generada correctamente.")


if __name__ == "__main__":
    main()
