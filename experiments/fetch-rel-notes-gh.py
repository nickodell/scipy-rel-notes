import requests
import json
url = "https://api.github.com/repos/scipy/scipy/releases"

def main():
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()
    with open('out.json', 'wt') as f:
        json.dump(data, f, indent=2)
    for release in data:
        tag_name = release["tag_name"]
        body = release["body"]
        if "rc" in tag_name:
            print(f"Ignoring {tag_name}")
            continue
        with open(f'existing_gh/{tag_name}-notes.md', 'wt') as f:
            f.write(body)


if __name__ == '__main__':
    main()
