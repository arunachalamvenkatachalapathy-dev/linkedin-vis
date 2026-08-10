import requests
import xml.etree.ElementTree as ET

def test_github():
    print("Testing GitHub API...")
    url = "https://api.github.com/search/repositories?q=decarbonization&sort=updated&per_page=3"
    res = requests.get(url, headers={"Accept": "application/vnd.github.v3+json"})
    if res.status_code == 200:
        for item in res.json().get("items", []):
            print(f"Repo: {item['full_name']} - {item['description']}")
    else:
        print("GitHub failed:", res.status_code)

def test_arxiv():
    print("\nTesting Arxiv API...")
    url = "http://export.arxiv.org/api/query?search_query=all:decarbonization&sortBy=submittedDate&sortOrder=descending&max_results=3"
    res = requests.get(url)
    if res.status_code == 200:
        root = ET.fromstring(res.text)
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            title = entry.find("{http://www.w3.org/2005/Atom}title").text.strip()
            summary = entry.find("{http://www.w3.org/2005/Atom}summary").text.strip()
            print(f"Paper: {title[:50]}...")
    else:
        print("Arxiv failed:", res.status_code)

if __name__ == "__main__":
    test_github()
    test_arxiv()
