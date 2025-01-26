import subprocess
import os
import re
import tempfile
from urllib.parse import urljoin

from natsort import natsorted
from Levenshtein import ratio as lev_ratio
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


def remove_non_article(soup):
    """Remove all text outside of <article>"""
    soup = soup.find("article")
    return soup


def remove_toc(soup):
    """Remove table of contents"""
    toc = soup.find("nav", {"id": "contents"})
    toc.decompose()
    return soup


def remove_css_classes(soup):
    """Remove all CSS classes"""
    for tag in soup.find_all():
        del tag['class']
    return soup


def remove_unknown_attr(soup):
    """Compare all element attrs to allowlist

    Remove attrs that are not specifically allowed."""
    attr_allowlist = {
        'href',
    }
    for tag in soup.find_all():
        for attr in list(tag.attrs):
            if attr in attr_allowlist:
                continue
            del tag[attr]
    return soup


def remove_permalinks(soup):
    """Remove link from section heading

    Removes all links with a text of '#'. Removes text of link
    as well."""
    for tag in soup.findAll("a"):
        if tag.text == '#':
            tag.decompose()
    return soup


def delink_internal_links(soup):
    """Unlink page-internal links

    Does not remove the contents of the link, because some links
    are semantically meaningful"""
    for tag in soup.findAll("a"):
        if tag.get('href', '').startswith('#'):
            tag.replace_with_children()
    return soup


def link_fixup(soup):
    """Resolve relative links"""
    base_address = 'https://scipy.github.io/devdocs/release/foo.html'
    for tag in soup.findAll("a"):
        tag['href'] = urljoin(base_address, tag['href'])
    return soup


def apply_tag_allowlist(soup):
    """Only allow subset of HTML tags

    This is used to avoid confusing Pandoc with <section>, for example."""
    tag_allowlist = {
        'a',
        'code',
        'h1',
        'h2',
        'h3',
        'h4',
        'h5',
        'h6',
        'li',
        'ul',
        'ol',
    }
    all_tags = set([tag.name for tag in soup.find_all()])
    for tag_type in all_tags:
        if tag_type not in tag_allowlist:
            for tag in soup.find_all(tag_type):
                tag.replace_with_children()
    return soup


def bs4_simplify_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    stages = [
        remove_non_article,
        remove_toc,
        remove_css_classes,
        remove_unknown_attr,
        remove_permalinks,
        delink_internal_links,
        link_fixup,
        apply_tag_allowlist,
    ]
    for stage in stages:
        soup = stage(soup)
    return str(soup)


def run_pandoc(html):
    # Make sure files have right extension, so that Pandoc can autodetect the type
    with tempfile.NamedTemporaryFile(suffix='.html', mode='wt') as htmlfile:
        with tempfile.NamedTemporaryFile(suffix='.md', mode='rt') as mdfile:
            htmlfile.write(html)
            subprocess.check_call(
                [
                    "pandoc",
                    # Don't re-wrap text
                    "--wrap=preserve",
                    "-o",
                    mdfile.name,
                    htmlfile.name
                ]
            )
            mdfile.seek(0)
            text = mdfile.read()
    return text


def drop_prs_and_issues(text):
    """Remove issues and PRs from release notes

    This is done to comply with GitHub's character limits on releases, which
    are roughly 125K characters."""
    text = re.sub(r"#+ Issues closed for .*", "", text, flags=re.DOTALL)
    return text


def reflow_text(text):
    text = re.sub(r"(\S)\n *([^-*\s])", "\\1 \\2", text)
    return text


def run_pipeline(tag_name):
    with open(f"sphinx_output/{tag_name.replace('v', '')}-notes.html", "rt") as f:
        html = f.read()
    html = bs4_simplify_html(html)
    text = run_pandoc(html)

    text = drop_prs_and_issues(text)
    text = reflow_text(text)
    # Convert to CRLF to match existing release notes
    text = text.replace("\n", "\r\n")
    with open(f"output/{tag_name}-notes.md", "wt") as f:
        f.write(text)


def main():
    for tag_name in get_versions():
    # for tag_name in ["v1.15.0"]:
        run_pipeline(tag_name)
        write_diffs(tag_name)
        report_difference(tag_name)


if __name__ == '__main__':
    main()
