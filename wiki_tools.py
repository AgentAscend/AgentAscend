import os

BASE_PATH = "/home/agentascend/projects/AgentAscend"
WIKI_PATH = os.path.join(BASE_PATH, "wiki")


def read_wiki_page(title):
    filename = f"{title}.md"
    path = os.path.join(WIKI_PATH, filename)

    if not os.path.exists(path):
        return f"Page '{title}' not found"

    with open(path, "r") as f:
        return f.read()


def list_wiki_pages():
    return os.listdir(WIKI_PATH)
