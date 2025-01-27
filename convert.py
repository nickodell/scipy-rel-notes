import subprocess
import argparse
import re
import tempfile
from urllib.parse import urljoin

from bs4 import BeautifulSoup


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
    for tag in soup.find_all("a"):
        if tag.text == '#':
            tag.decompose()
    return soup


def delink_internal_links(soup):
    """Unlink page-internal links

    Does not remove the contents of the link, because that sometimes
    makes the text make no sense."""
    for tag in soup.find_all("a"):
        if tag.get('href').startswith('#'):
            tag.replace_with_children()
    return soup


def link_fixup(soup):
    """Resolve relative links"""
    global base_address
    for tag in soup.find_all("a"):
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


def run_pandoc(html, rewrap_text=True):
    # Make sure files have right extension, so that Pandoc can autodetect the type
    wrap_setting = "--wrap=none" if rewrap_text else "--wrap=preserve"
    with tempfile.NamedTemporaryFile(suffix='.html', mode='wt') as htmlfile:
        with tempfile.NamedTemporaryFile(suffix='.md', mode='rt') as mdfile:
            htmlfile.write(html)
            subprocess.check_call(
                [
                    "pandoc",
                    # Don't re-wrap text
                    wrap_setting,
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


def run_pipeline(input_file, output_file):
    with open(input_file, "rt") as f:
        html = f.read()
    html = bs4_simplify_html(html)
    text = run_pandoc(html, rewrap_text=True)

    text = drop_prs_and_issues(text)

    # Convert to CRLF to match existing release notes
    text = text.replace("\n", "\r\n")

    with open(output_file, "wt") as f:
        f.write(text)


def main():
    global base_address
    parser = argparse.ArgumentParser(
        prog="convert.py",
        description="Generates GitHub Flavored Markdown from HTML release notes"
    )
    parser.add_argument(
        "input_html"
    )
    parser.add_argument(
        "output_md"
    )
    parser.add_argument(
        "--base-address",
        default='https://scipy.github.io/devdocs/release/foo.html',
        help='Where the release notes would be placed online. Used for relative links'
    )

    args = parser.parse_args()
    base_address = args.base_address
    run_pipeline(args.input_html, args.output_md)


if __name__ == '__main__':
    main()
