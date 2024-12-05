import os
import re
from collections import defaultdict
from github3 import GitHub, exceptions

# Fetch the token from environment variables
token = os.getenv("NEW_GITHUB_TOKEN", None)
if token is None or token == "":
    raise ValueError("Environment variable NEW_GITHUB_TOKEN is either not set or empty.")
print(f"Token received: {token[:5]}{'*' * (len(token) - 5)}")

# Authenticate with GitHub
try:
    gh = GitHub(token=token)
except exceptions.AuthenticationFailed:
    raise RuntimeError("Authentication failed. Check your NEW_GITHUB_TOKEN.")

# Utility for escaping HTML
html_escape_table = {
    ">": "&gt;",
    "<": "&lt;",
}

def html_escape(text: str) -> str:
    return "".join(html_escape_table.get(c, c) for c in text)

# Utility for generating unique fragment IDs
base_fragment_id_counters: dict[int] = {}

def get_fragment_id(heading: str) -> str:
    base_fragment_id = re.sub("[^a-z-]+", "", heading.lower().replace(" ", "-"))
    if base_fragment_id not in base_fragment_id_counters:
        base_fragment_id_counters[base_fragment_id] = 1
        return base_fragment_id

    fragment_id = f"{base_fragment_id}-{base_fragment_id_counters[base_fragment_id]}"
    base_fragment_id_counters[base_fragment_id] += 1
    return fragment_id

# Fetch starred repositories and organize by language
repo_list_dict = defaultdict(list)
try:
    for s in gh.starred_by("baditaflorin"):
        repo_list_dict[s.language or "Miscellaneous"].append(
            [s.full_name, s.html_url, html_escape((s.description or "").strip())]
        )
except exceptions.AuthenticationFailed:
    raise RuntimeError("Failed to fetch starred repositories. Check your token.")

# Sort and format repository data
repo_list_of_lists = sorted(repo_list_dict.items(), key=lambda r: r[0])

new_readme_content = "## Languages\n\n{}\n{}\n".format(
    "\n".join(
        f"*   [{language}](#{get_fragment_id(language)})"
        for language, _ in repo_list_of_lists
    ),
    "\n".join(
        f"\n## {language}\n\n"
        + "\n".join(
            f"*   [{name}]({url})" + (f": {desc}" if desc else "")
            for name, url, desc in repo_list
        )
        for language, repo_list in repo_list_of_lists
    ),
).encode()

# Fetch the README file from the repository
try:
    repo = gh.repository("baditaflorin", "github-stars")
    readme = repo.readme()
except exceptions.AuthenticationFailed:
    raise RuntimeError("Failed to access the repository. Check your token and repository permissions.")
except exceptions.NotFoundError:
    raise RuntimeError("Repository or README file not found.")

# Update README if content has changed
if new_readme_content != readme.decoded:
    try:
        readme.update("Update list of starred repositories", new_readme_content)
    except exceptions.AuthenticationFailed:
        raise RuntimeError("Failed to update README. Check your token and repository permissions.")
    except exceptions.UnprocessableEntity:
        raise RuntimeError("Failed to process the update request. Check the format of the update.")

print("README updated successfully.")
