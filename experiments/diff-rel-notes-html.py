import subprocess
import os
import re
import tempfile
from urllib.parse import urljoin

from natsort import natsorted
from Levenshtein import ratio as lev_ratio


import bs4
from bs4 import BeautifulSoup


def get_versions():
    filenames = natsorted(os.listdir('existing_gh'))
    for filename in filenames:
        if (
            ".1-notes" in filename or
            ".2-notes" in filename or
            ".3-notes" in filename or
            ".4-notes" in filename
            ):
            continue
        filename = filename.replace('-notes.md', '')
        yield filename



def write_diffs(tag_name):
    proc = subprocess.run(
        f"diff existing_gh/{tag_name}-notes.md "
        f"output/{tag_name}-notes.md > diff_output/{tag_name}.diff",
        shell=True
    )
    # 0 = no difference, 1 = difference
    assert proc.returncode in [0, 1]


def report_difference(tag_name):
    with open(f"existing_gh/{tag_name}-notes.md", "rt") as f:
        existing = f.read()
    with open(f"output/{tag_name}-notes.md", "rt") as f:
        output = f.read()
    ratio = lev_ratio(existing, output)
    print(f"Difference for {tag_name} is {(1-ratio)*100:.2f}%")


def preproc(text):
    soup = BeautifulSoup(text, "html.parser")
    soup = soup.find("article")
    # Remove table of contents
    toc = soup.find("nav", {"id": "contents"})
    toc.decompose()

    for tag in soup.find_all():
        del tag['class']
    attr_strip = {
        "a": ["id", "title"],
    }
    for tag_type in attr_strip:
        for tag in soup.findAll(tag_type):
            for attribute in attr_strip[tag_type]:
                del tag[attribute]
    for tag in soup.findAll("a"):
        # print(repr(tag.text))
        if tag.text == '#':
            tag.decompose()
        elif tag.get('href').startswith('#'):
            tag.replaceWithChildren()
        else:
            base_address = 'https://scipy.github.io/devdocs/release/foo.html'
            tag['href'] = urljoin(base_address, tag['href'])


    tag_allowlist = {
        'a',
        'code',
        'h1',
        'h2',
        'h3',
        'li',
        'ul',
    }
    all_tags = set([tag.name for tag in soup.find_all()])
    for tag_type in all_tags:
        if tag_type not in tag_allowlist:
            for tag in soup.findAll(tag_type):
                tag.replaceWithChildren()
    return str(soup)


def run_pipeline(tag_name):
    # sphinx_output/1.15.0-notes.html
    with open(f"sphinx_output/{tag_name.replace('v', '')}-notes.html", "rt") as f:
        text = f.read()
    text = preproc(text)
    # text = convert_html_to_md(text)
    # text = text.replace("\n\n", "\n")
    # text = text.replace("\n", "\r\n")
    # text = text.replace("-   ", "- ")
    # text = text.replace("    ", "  ")
    # text = text.replace("`", "``")
    # text = re.sub(r"-", "", text, flags=re.DOTALL)
    # text = re.sub(r"([- ])   \b", "\\1 ", text)
    # text = re.sub(r'::: {#.*section}', '', text)
    text = re.sub(r"Issues closed for .*", "", text, flags=re.DOTALL)
    with open(f"output/{tag_name}-notes.md", "wt") as f:
        f.write(text)


def main():
    # for tag_name in get_versions():
    for tag_name in ["v1.15.0"]:
        run_pipeline(tag_name)
        write_diffs(tag_name)
        report_difference(tag_name)
        break


if __name__ == '__main__':
    main()
