"""Tests for the Markdown to Confluence converter."""

import logging
import re
import textwrap

import markdown

from mkdocs_to_confluence.markdown_to_confluence import ConfluenceExtension

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger().setLevel(logging.DEBUG)  # Set root logger to DEBUG
log = logging.getLogger("TESTS")


# Define the common extensions for Python-Markdown
COMMON_MKDOCS_EXTENSIONS = [
    "tables",
    "attr_list",
    "md_in_html",
    "pymdownx.highlight",
    "pymdownx.superfences",
    "pymdownx.details",
    "sane_lists",
    "fenced_code",
    "admonition",
    "def_list",
    "footnotes",
    "abbr",
    "pymdownx.tasklist",
    "pymdownx.emoji",
    "pymdownx.keys",
    "pymdownx.mark",
    "pymdownx.caret",
    "pymdownx.tilde",
]


def assert_xml_equal(actual, expected):
    """Compare XML strings ignoring whitespace between tags."""
    # Remove whitespace between tags: > space <  -> ><
    normalized_actual = re.sub(r">\s+<", "><", actual).strip()
    normalized_expected = re.sub(r">\s+<", "><", expected).strip()
    # Also collapse internal whitespace
    normalized_actual = re.sub(r"\s+", " ", normalized_actual)
    normalized_expected = re.sub(r"\s+", " ", normalized_expected)

    assert normalized_actual == normalized_expected, f"\nExpected:\n{normalized_expected}\nActual:\n{normalized_actual}"


def test_text_formatting():
    """Test conversion of basic text formatting."""
    md_text = textwrap.dedent("""
        **Bold text** and *italic text* and ***bold italic***

        ~~Strikethrough text~~ for deprecated content

        ==Highlighted text== for emphasis

        <ins>Inserted text</ins> for new additions

        H~2~O for subscript and E=mc^2^ for superscript
    """)
    expected = """
<p><strong>Bold text</strong> and <em>italic text</em> and <strong><em>bold italic</em></strong></p>
<p><s>Strikethrough text</s> for deprecated content</p>
<p><span style="background-color: #ffff00;">Highlighted text</span> for emphasis</p>
<p><u>Inserted text</u> for new additions</p>
<p>H<sub>2</sub>O for subscript and E=mc<sup>2</sup> for superscript</p>
"""
    md = markdown.Markdown(extensions=COMMON_MKDOCS_EXTENSIONS + [ConfluenceExtension()])
    assert_xml_equal(md.convert(md_text), expected)


def test_lists():
    """Test conversion of ordered, unordered, and task lists."""
    # Use 4 spaces for nesting
    md_text = textwrap.dedent("""
        **Unordered:**

        - First level
            - Second level
                - Third level

        **Ordered:**

        1. First step
        2. Second step
            1. Sub-step A
            2. Sub-step B

        **Task List:**

        - [x] Completed task
        - [ ] Pending task
    """)
    expected = """
<p><strong>Unordered:</strong></p>
<ul>
<li>First level<ul>
<li>Second level<ul>
<li>Third level</li>
</ul>
</li>
</ul>
</li>
</ul>
<p><strong>Ordered:</strong></p>
<ol>
<li>First step</li>
<li>Second step<ol>
<li>Sub-step A</li>
<li>Sub-step B</li>
</ol>
</li>
</ol>
<p><strong>Task List:</strong></p>
<ac:task-list>
<ac:task>
<ac:task-status>complete</ac:task-status>
<ac:task-body> Completed task</ac:task-body>
</ac:task>
<ac:task>
<ac:task-status>incomplete</ac:task-status>
<ac:task-body> Pending task</ac:task-body>
</ac:task>
</ac:task-list>
"""
    md = markdown.Markdown(extensions=COMMON_MKDOCS_EXTENSIONS + [ConfluenceExtension()])
    assert_xml_equal(md.convert(md_text), expected)


def test_admonitions():
    """Test conversion of admonitions."""
    md_text = textwrap.dedent("""
        !!! note "Information Note"
            This is a note admonition.

        !!! warning "Important Warning"
            Always backup your data.
    """)
    expected = """
<ac:structured-macro ac:name="info">
<ac:parameter ac:name="title">Information Note</ac:parameter>
<ac:rich-text-body>
<p>This is a note admonition.</p>
</ac:rich-text-body>
</ac:structured-macro>
<ac:structured-macro ac:name="note">
<ac:parameter ac:name="title">Important Warning</ac:parameter>
<ac:rich-text-body>
<p>Always backup your data.</p>
</ac:rich-text-body>
</ac:structured-macro>
"""
    md = markdown.Markdown(extensions=COMMON_MKDOCS_EXTENSIONS + [ConfluenceExtension()])
    assert_xml_equal(md.convert(md_text), expected)


def test_links_and_images():
    """Test conversion of links and images."""
    md_text = textwrap.dedent("""
        [Go to Another Page](another_page.md)

        ![Example Diagram](assets/diagram.png)
    """)
    expected = """
<p><ac:link><ri:page ri:content-title="Another Page" /></ac:link></p>
<p><ac:image ac:alt="Example Diagram"><ri:attachment ri:filename="diagram.png" /></ac:image></p>
"""
    md = markdown.Markdown(extensions=COMMON_MKDOCS_EXTENSIONS + [ConfluenceExtension()])
    assert_xml_equal(md.convert(md_text), expected)


def test_local_links():
    """Test conversion of links and images."""
    md_text = textwrap.dedent("""
        [Go to Heading One](#heading-one)

        ## Heading One
    """)
    expected = """
<p><ac:link ac:anchor="HeadingOne"><ac:plain-text-link-body><![CDATA[Go to Heading One]]></ac:plain-text-link-body></ac:link></p>
<h2>Heading One</h2>
"""
    md = markdown.Markdown(extensions=COMMON_MKDOCS_EXTENSIONS + [ConfluenceExtension()])
    assert_xml_equal(md.convert(md_text), expected)


def test_footnotes():
    """Test conversion of footnotes."""
    md_text = textwrap.dedent("""
        Text with footnote[^1].

        [^1]: Footnote content.
    """)
    md = markdown.Markdown(extensions=COMMON_MKDOCS_EXTENSIONS + [ConfluenceExtension()])
    output = md.convert(md_text)
    assert '<sup id="fnref:1">' in output
    assert '<div class="footnote">' in output
    assert "<ol>" in output
    assert '<li id="fn:1">' in output


def test_keyboard_keys():
    """Test conversion of keyboard keys."""
    md_text = "Press ++ctrl+c++"
    md = markdown.Markdown(extensions=COMMON_MKDOCS_EXTENSIONS + [ConfluenceExtension()])
    output = md.convert(md_text)
    assert 'class="keys"' in output
    assert 'class="key-control"' in output


def test_tables():
    """Test conversion of tables."""
    md_text = textwrap.dedent("""
        | Header 1 | Header 2 | Header 3 |
        | -------- | -------- | -------- |
        | Row 1 Col 1 | Row 1 Col 2 | Row 1 Col 3 |
        | Row 2 Col 1 | Row 2 Col 2 | Row 2 Col 3 |
    """)
    expected = """
<p>
<table data-layout="full-width">
<thead>
<tr>
<th>Header 1</th>
<th>Header 2</th>
<th>Header 3</th>
</tr>
</thead>
<tbody>
<tr>
<td>Row 1 Col 1</td>
<td>Row 1 Col 2</td>
<td>Row 1 Col 3</td>
</tr>
<tr>
<td>Row 2 Col 1</td>
<td>Row 2 Col 2</td>
<td>Row 2 Col 3</td>
</tr>
</tbody>
</table>
</p>
"""
    md = markdown.Markdown(extensions=COMMON_MKDOCS_EXTENSIONS + [ConfluenceExtension()])
    assert_xml_equal(md.convert(md_text), expected)


def test_emoji():
    """Test conversion of emojis."""
    md_text = ":rocket:"
    md = markdown.Markdown(extensions=COMMON_MKDOCS_EXTENSIONS + [ConfluenceExtension()])
    output = md.convert(md_text)
    # Expect ac:image tag (normalized to <tag ... /> by Postprocessor)
    assert "<ac:image" in output
    assert "ri:value=" in output
    assert "1f680.png" in output
