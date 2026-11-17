"""Rebuilds the dynamic sections of README.md from the GitHub API.

Sections (between marker comments):
  <!--START_SECTION:activity--> ... <!--END_SECTION:activity-->
  <!--START_SECTION:projects--> ... <!--END_SECTION:projects-->
"""
import os
import re
import requests

USER = "Adwaith-vinod"
TOKEN = os.environ.get("GH_TOKEN")
README = "README.md"

HEADERS = {"Accept": "application/vnd.github+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def get(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_repos():
    repos, page = [], 1
    while True:
        batch = get(
            f"https://api.github.com/users/{USER}/repos",
            {"per_page": 100, "page": page, "type": "owner", "sort": "pushed"},
        )
        if not batch:
            break
        repos += batch
        page += 1
    # skip forks, archived repos and the profile repo itself
    repos = [
        r for r in repos
        if not r["fork"] and not r["archived"] and r["name"].lower() != USER.lower()
    ]
    repos.sort(key=lambda r: r["pushed_at"], reverse=True)
    return repos


def clean(text):
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def projects_block(repos):
    if not repos:
        return "_No public projects yet._"
    rows = [
        "| Project | What it does | Stack | ⭐ | Last push |",
        "|---------|--------------|-------|----|-----------|",
    ]
    for r in repos:
        name = f"[**{r['name']}**]({r['html_url']})"
        desc = clean(r["description"]) or "_No description yet_"
        lang = f"`{r['language']}`" if r["language"] else "—"
        pushed = r["pushed_at"][:10]
        rows.append(f"| {name} | {desc} | {lang} | {r['stargazers_count']} | {pushed} |")
    return "\n".join(rows)


def activity_block(repos, limit=6):
    lines = []
    for r in repos[:limit]:
        try:
            commits = get(
                f"https://api.github.com/repos/{USER}/{r['name']}/commits",
                {"per_page": 1, "author": USER},
            )
        except requests.HTTPError:
            continue
        if not commits:
            continue
        c = commits[0]
        msg = clean(c["commit"]["message"].split("\n")[0])[:80]
        date = c["commit"]["author"]["date"][:10]
        lines.append(
            f"- `{date}` · [{r['name']}]({r['html_url']}) — {msg} "
            f"([{c['sha'][:7]}]({c['html_url']}))"
        )
    return "\n".join(lines) or "_No recent commits._"


def replace_section(text, name, content):
    pattern = rf"(<!--START_SECTION:{name}-->).*?(<!--END_SECTION:{name}-->)"
    if not re.search(pattern, text, flags=re.DOTALL):
        raise SystemExit(f"Markers for section '{name}' not found in {README}")
    return re.sub(
        pattern,
        lambda m: f"{m.group(1)}\n{content}\n{m.group(2)}",
        text,
        flags=re.DOTALL,
    )


def main():
    repos = fetch_repos()
    with open(README, encoding="utf-8") as f:
        text = f.read()

    text = replace_section(text, "projects", projects_block(repos))
    text = replace_section(text, "activity", activity_block(repos))

    with open(README, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Updated README with {len(repos)} projects.")


if __name__ == "__main__":
    main()
