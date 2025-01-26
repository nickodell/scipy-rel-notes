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
    attr_strip = {
        # "a": ["class", "id"],
        # "code": ["class"],
        # "span": ["class"],
    }
    for tag_type in attr_strip:
        for tag in soup.findAll(tag_type):
            for attribute in attr_strip[tag_type]:
                del tag[attribute]
    for tag in soup.findAll("section"):
        tag.replaceWithChildren()
    return str(soup)


def convert_html_to_md(text):
    soup = BeautifulSoup(text, "html.parser")
    markdown = []
    ignored_elem = [
        "[document]",
        "article",
        # "section",
        "p",
        "li",
        "span",
    ]
    indent_level = 0
    def p(s):
        p_no_indent(s.replace("\n", "\n" + "  " * indent_level))
    def p_no_indent(s):
        markdown.append(s)
    def handle_header(elem):
        p("\n# ")
        walk_children(elem)
        p("\n")
    def handle_anchor(elem):
        base_address = 'https://scipy.github.io/devdocs/release/foo.html'
        internal = elem['href'].startswith('#')
        permalink = 'headerlink' in elem['class']
        if not internal:
            p("[")
            walk_children(elem)
            p("](")
            p(urljoin(base_address, elem['href']))
            p(")")
        elif permalink:
            # Ignore permalink
            pass
        else:
            walk_children(elem)
    def handle_code(elem):
        p_no_indent("``")
        walk_children(elem)
        p_no_indent("``")
        # if "`" in elem.text:
        # else:
        #     p_no_indent("`")
        #     walk_children(elem)
        #     p_no_indent("`")
    def handle_ul(elem):
        nonlocal indent_level
        indent_level += 1
        first = True
        for child in elem.children:
            if child.name == "li":
                p_no_indent("- ")
                walk(child)
            p_no_indent("\n")
        indent_level -= 1
    def walk_children(elem):
        for child in elem.children:
            walk(child)
    def walk(elem):
        # print(elem.name)
        if isinstance(elem, bs4.element.Tag):
            # if 'migration guide' in elem.text and len(elem.text) < 100:
            #     print(elem)
            name = elem.name
            if name in ["h1", "h2", "h3"]:
                handle_header(elem)
            elif name == "a":
                handle_anchor(elem)
            elif name == "ul":
                handle_ul(elem)
            # elif name == "p":
            #     p(elem.text)
            elif name == "code":
                handle_code(elem)
            else:
                if elem.name not in ignored_elem:
                    p(" " + elem.name + " ")
                walk_children(elem)
        if isinstance(elem, bs4.element.NavigableString):
            p(elem.string)
    walk(soup)
    # for tag in soup():
    #     # print(tag.name, tag.text)
    #     name = tag.name
    #     if isinstance(tag, bs4.element.NavigableString):
    #         p(tag.string)
    #     else:
    #         pass
    return "".join(markdown)


def run_pipeline(tag_name):
    # sphinx_output/1.15.0-notes.html
    with open(f"sphinx_output/{tag_name.replace('v', '')}-notes.html", "rt") as f:
        text = f.read()
    text = preproc(text)
    text = convert_html_to_md(text)
    text = text.replace("\n\n", "\n")
    text = text.replace("\n", "\r\n")
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
