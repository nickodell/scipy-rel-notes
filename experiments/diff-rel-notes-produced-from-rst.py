import subprocess
import os
import re
import tempfile

from natsort import natsorted
from Levenshtein import ratio as lev_ratio


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


def run_pipeline(tag_name):
    with open(f"rst_notes/{tag_name}-notes.rst", "rt") as f:
        text = f.read()
    text = re.sub(r"\s*\**\s*Issues closed for.*", "", text, flags=re.DOTALL)
    with tempfile.NamedTemporaryFile(suffix='.rst', mode='wt') as rstfile:
        with tempfile.NamedTemporaryFile(suffix='.md', mode='rt') as mdfile:
            rstfile.write(text)
            proc = subprocess.check_call(
                [
                    "pandoc",
                    # "-s",
                    "--wrap=preserve",
                    # "--reference-links=false",
                    # "--to", "markdown_strict",
                    "-o",
                    mdfile.name,
                    rstfile.name
                ]
            )
            mdfile.seek(0)
            text = mdfile.read()
    text = text.replace("\n", "\r\n")
    text = text.replace("-   ", "- ")
    text = text.replace("    ", "  ")
    text = text.replace("`", "``")
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
