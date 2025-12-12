import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor
from markdown.treeprocessors import Treeprocessor

log = logging.getLogger("MARKDOWN")  # Use Markdown's logger


class ConfluenceTreeprocessor(Treeprocessor):
    def run(self, root):
        log.debug("ConfluenceTreeprocessor running...")
        self._clean_headers(root)
        self._convert_code_blocks(root)
        self._convert_admonitions(root)
        self._convert_images_and_links(root)
        self._convert_tables(root)
        self._convert_inline_formatting(root)

    def _convert_admonitions(self, root):
        log.debug("Converting admonitions...")
        # Admonitions are divs with class "admonition <type>"
        for div_element in root.findall(".//div"):
            if "class" in div_element.attrib and "admonition" in div_element.attrib["class"]:
                log.debug(f"Found admonition: {div_element.attrib['class']}")
                classes = div_element.attrib["class"].split()
                admonition_type = "note"  # default
                for cls in classes:
                    if cls != "admonition":
                        admonition_type = cls
                        break

                # Map standard admonition types to Confluence macro names
                # Confluence macros: info, tip, note, warning
                macro_name = "info"
                if admonition_type in ["note", "abstract", "summary", "tldr"]:
                    macro_name = "info"
                elif admonition_type in ["tip", "hint", "important", "success", "check", "done"]:
                    macro_name = "tip"
                elif admonition_type in ["warning", "caution", "attention"]:
                    macro_name = "note"
                elif admonition_type in ["danger", "error", "failure", "bug", "missing"]:
                    macro_name = "warning"
                else:
                    # Handle special case? Or just ignore?
                    pass

                ac_macro = Element("ac:structured-macro", attrib={"ac:name": macro_name})

                # Handle title
                title_element = None
                # The first child is usually p.admonition-title
                if (
                    len(div_element) > 0
                    and div_element[0].tag == "p"
                    and "admonition-title" in div_element[0].attrib.get("class", "")
                ):
                    title_element = div_element[0]
                    title_text = title_element.text
                    if title_text:
                        ac_parameter = SubElement(ac_macro, "ac:parameter", attrib={"ac:name": "title"})
                        ac_parameter.text = title_text

                ac_body = SubElement(ac_macro, "ac:rich-text-body")

                # Move children to body (excluding title)
                for child in div_element:
                    if child is not title_element:
                        ac_body.append(child)

                self._replace_element(root, div_element, ac_macro)

    def _convert_code_blocks(self, root):
        log.debug("Converting code blocks...")
        # Find all pre elements
        for pre_element in root.findall(".//pre"):
            # Check if it contains a code element
            code_element = pre_element.find("code")
            if code_element is not None:
                log.debug(f"Found code block: {tostring(pre_element).decode()}")

                # Create the macro element
                ac_macro = Element("ac:structured-macro", attrib={"ac:name": "code"})

                # Determine language
                language = "text"  # default
                if "class" in code_element.attrib:
                    classes = code_element.attrib["class"].split()
                    for cls in classes:
                        if cls.startswith("language-"):
                            language = cls.replace("language-", "")
                            break

                # Add language parameter
                ac_parameter = SubElement(ac_macro, "ac:parameter", attrib={"ac:name": "language"})
                ac_parameter.text = language

                # Add plain-text-body with CDATA
                # ElementTree doesn't support CDATA natively in a simple way for just one element.
                # However, for Confluence, the content of plain-text-body is usually just text.
                # Special characters need to be escaped if we treat it as standard XML text,
                # but Confluence expects CDATA for code blocks to preserve formatting and special chars.
                # Since we are generating an ElementTree, setting .text will automatically escape <, >, &
                # which might be what we want if we don't strictly enforce CDATA wrapping in the output string yet.
                # BUT, Confluence storage format specifically uses <ac:plain-text-body><![CDATA[...]]></ac:plain-text-body>
                # To achieve this with standard ElementTree is tricky.
                # A common workaround is to use a special marker or just let it escape and rely on Confluence to interpret it,
                # but usually CDATA is required for code.

                # For now, let's just set the text and see if `tostring` escapes it correctly.
                # If Confluence requires literal CDATA wrapping, we might need a post-processing step
                # or a custom serializer.
                # Let's try standard text assignment first.
                ac_body = SubElement(ac_macro, "ac:plain-text-body")
                ac_body.text = code_element.text

                # Replace pre with macro
                self._replace_element(root, pre_element, ac_macro)

    def _clean_headers(self, root):
        log.debug("Cleaning headers...")
        for i in range(1, 7):  # h1 to h6
            for header_element in root.findall(f".//h{i}"):
                log.debug(f"Found header: {header_element.tag} with attribs: {header_element.attrib}")
                if "id" in header_element.attrib:
                    log.debug(f"Removing id: {header_element.attrib['id']} from {header_element.tag}")
                    del header_element.attrib["id"]

                # Remove any headerlink anchors added by the TOC extension
                for child in list(header_element):  # Iterate over a copy to allow modification
                    if child.tag == "a" and child.attrib.get("class") == "headerlink":
                        log.debug(f"Removing headerlink: {tostring(child).decode()} from {header_element.tag}")
                        header_element.remove(child)

    def _convert_images_and_links(self, root):
        log.debug("Converting images and links...")
        for img_element in root.findall(".//img"):
            log.debug(f"Found img: {tostring(img_element).decode()}")
            src = img_element.attrib.get("src", "")
            alt = img_element.attrib.get("alt", "")

            if not re.match(r"^(http|https)://", src):
                ac_image = Element("ac:image", attrib={"ac:alt": alt})
                ri_attachment = SubElement(ac_image, "ri:attachment", attrib={"ri:filename": Path(src).name})
                log.debug(f"Converted img to attachment: {tostring(ac_image).decode()}")
            else:
                ac_image = Element("ac:image", attrib={"ac:alt": alt})
                ri_url = SubElement(ac_image, "ri:url", attrib={"ri:value": src})
                log.debug(f"Converted img to url: {tostring(ac_image).decode()}")

            # Replace the img element with ac:image
            # ElementTree doesn't have parent pointers, so we find and replace
            self._replace_element(root, img_element, ac_image)

        # Handle internal links - MkDocs produces href="#anchor" or href="page#anchor"
        # Confluence links are typically handled by page titles or content IDs,
        # but internal page anchors remain as href="#anchor"
        for a_element in root.findall(".//a"):
            href = a_element.attrib.get("href", "")
            if href.startswith("#"):
                # Internal anchor link. Ensure only href is present.
                log.debug(f"Found anchor link: {tostring(a_element).decode()} - cleaning attributes")
                a_element.attrib = {"href": href}  # Keep only href
            elif not re.match(r"^(http|https)://", href):
                # Assume internal page link (e.g., ../page.md)
                pass

    def _convert_tables(self, root):
        log.debug("Converting tables...")

        # Build parent map once before modifications to allow tree manipulation
        # This map needs to be updated or rebuilt if structural changes occur in the loop.
        # A safer approach is to collect elements first, then modify.
        tables_to_process = list(root.findall(".//table"))

        for table_element in tables_to_process:
            log.debug(f"Found table: {tostring(table_element).decode()}")

            # 1. Add data-layout attribute
            table_element.attrib["data-layout"] = "full-width"
            log.debug(f"Added data-layout to table: {tostring(table_element).decode()}")

            # 2. Wrap table in a <p> tag
            p_element = Element("p")

            # Find the parent of the table_element
            # ElementTree does not have direct parent pointers, so we search from the root.
            # This is inefficient if called many times, but for a few tables it's fine.
            parent = None
            for p in root.iter():
                for child in p:
                    if child == table_element:
                        parent = p
                        break
                if parent is not None:
                    break

            if parent is not None:
                # Find the index of the table_element in its parent's children
                index = list(parent).index(table_element)

                # Remove the table_element from its original parent
                parent.remove(table_element)

                # Append the table_element to the new p_element
                p_element.append(table_element)

                # Insert the new p_element (which now contains the table) into the parent at the same index
                parent.insert(index, p_element)
                log.debug(f"Wrapped table in p tag and re-inserted at index {index}.")
            else:
                log.warning(f"Could not find parent for table element: {tostring(table_element).decode()}")

            # Handle text-align styles within table cells (existing logic)
            for cell in table_element.findall(".//th") + table_element.findall(".//td"):
                style_attr = cell.attrib.get("style", "")
                if "text-align" in style_attr:
                    match = re.search(r"text-align:\s*(left|center|right);", style_attr)
                    if match:
                        align_value = match.group(1)
                        log.debug(f"Found table cell with style: {style_attr}. Setting align={align_value}")
                        cell.attrib["align"] = align_value
                        # Remove the text-align from style attribute
                        cell.attrib["style"] = re.sub(r"text-align:\s*(left|center|right);", "", style_attr).strip()
                        if not cell.attrib["style"]:
                            del cell.attrib["style"]

    def _replace_element(self, root, old_element, new_element):
        parent_map = {c: p for p in root.iter() for c in p}
        parent = parent_map.get(old_element)
        if parent is not None:
            for i, child in enumerate(parent):
                if child == old_element:
                    parent[i] = new_element
                    log.debug(f"Replaced {old_element.tag} with {new_element.tag}")
                    return True

        # Debugging failure
        log.warning(f"Failed to replace element {old_element.tag}.")
        if parent is None:
            log.warning("Reason: Parent not found in root.iter() map.")
            # Check if element is root?
            if old_element == root:
                log.warning("Reason: Element is root.")
        else:
            log.warning("Reason: Element found in parent map but not in parent's children list (should not happen).")
        return False

    def _convert_inline_formatting(self, root):
        log.debug("Converting inline formatting...")
        # Handle mark -> span style background
        for elem in root.findall(".//mark"):
            elem.tag = "span"
            elem.attrib["style"] = "background-color: #ffff00;"  # Standard yellow highlight

        # Handle del -> s (Confluence uses s or del? Editor produces s usually, storage format allows del/s)
        # Python-Markdown uses del by default. Confluence usually accepts it.
        # But let's standardise if needed. s is shorter.
        for elem in root.findall(".//del"):
            elem.tag = "s"


class ConfluencePostprocessor(Postprocessor):
    def run(self, text):
        log.debug(f"ConfluencePostprocessor running on text length: {len(text)}")

        # Fix boolean attributes for XML parsing
        # pymdownx tasklists produce <input disabled checked> which is not valid XML
        text = re.sub(r"(\s)(checked|disabled)(?=[\s/>])", r'\1\2="\2"', text)

        namespaces = 'xmlns:ac="http://www.atlassian.com/schema/confluence/4/ac/" xmlns:ri="http://www.atlassian.com/schema/confluence/4/ri/"'
        wrapped_text = f"<root {namespaces}>{text}</root>"
        try:
            ET.register_namespace("ac", "http://www.atlassian.com/schema/confluence/4/ac/")
            ET.register_namespace("ri", "http://www.atlassian.com/schema/confluence/4/ri/")
            root = ET.fromstring(wrapped_text)
            log.debug(f"Parsed root: {root.tag}. Child count: {len(root)}")
        except ET.ParseError as e:
            log.warning(f"Failed to parse output as XML in ConfluencePostprocessor: {e}. Skipping fixups.")
            return text

        # 1. Convert task lists (ul.task-list)
        for ul in root.findall(".//ul"):
            if "task-list" in ul.attrib.get("class", "").split():
                log.debug("Found task list in Postprocessor")
                ac_list = Element("ac:task-list")

                for li in ul.findall("li"):
                    ac_task = SubElement(ac_list, "ac:task")
                    ac_status = SubElement(ac_task, "ac:task-status")
                    ac_body = SubElement(ac_task, "ac:task-body")

                    status = "incomplete"
                    input_elem = li.find("input")
                    if input_elem is not None:
                        if input_elem.get("checked") is not None:
                            status = "complete"

                        # Preserve text after input (e.g. " Task description")
                        if input_elem.tail:
                            if li.text:
                                li.text += input_elem.tail
                            else:
                                li.text = input_elem.tail

                        li.remove(input_elem)

                    ac_status.text = status

                    if li.text:
                        ac_body.text = li.text
                    for child in li:
                        ac_body.append(child)

                self._replace_element(root, ul, ac_list)

        # 2. Convert ins -> u
        for ins in root.findall(".//ins"):
            ins.tag = "u"

        # Always serialize back to ensure normalization
        new_text = tostring(root, encoding="unicode", method="xml")
        if new_text.startswith("<root") and new_text.endswith("</root>"):
            start_content = new_text.find(">") + 1
            new_text = new_text[start_content:-7]
        return new_text

    def _replace_element(self, root, old_element, new_element):
        parent_map = {c: p for p in root.iter() for c in p}
        parent = parent_map.get(old_element)
        if parent is not None:
            for i, child in enumerate(parent):
                if child == old_element:
                    parent[i] = new_element
                    return True
        return False


class ConfluenceExtension(Extension):
    def __init__(self, *args, **kwargs):
        self.config = {"base_url": ["", "Base URL for Confluence instance (e.g., https://your.atlassian.net/wiki)"]}
        super().__init__(*args, **kwargs)

    def extendMarkdown(self, md):
        # Register the treeprocessor
        # ConfluenceTreeprocessor runs after all other Markdown processing
        # and transforms the standard HTML ElementTree into Confluence XHTML.
        # Priority must be < 20 (InlineProcessor) to ensure inline elements are converted first.
        md.treeprocessors.register(ConfluenceTreeprocessor(md), "confluence_treeprocessor", 5)

        # Register Postprocessor
        md.postprocessors.register(ConfluencePostprocessor(md), "confluence_postprocessor", 0)

        # Ensure the output format is xhtml
        md.output_format = "xhtml"
        md.stripTOPLEVEL = False  # Prevent stripping the root element if it's a fragment


def makeExtension(**kwargs):
    return ConfluenceExtension(**kwargs)
