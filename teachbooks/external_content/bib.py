"""Functionality to read write and compare .bib files."""
from dataclasses import dataclass
import re
from pathlib import Path

import click

from teachbooks.external_content.config import CLICK_WARNING_KWARGS


BIB_ENTRY_RE = re.compile(r"@(\w+){([\w:-]+)")


@dataclass
class BibEntry:
    """Contains the essential information of a bib entry."""
    entrytype: str
    citekey: str
    content: dict[str,str]


def read_bibfile(file: Path) -> list[BibEntry]:
    """Read bib file into list of BibEntry objects.

    :param file: Path to the .bib file.
    :return: List of .bib file entries.
    """
    with file.open("r") as f:
        lines = f.readlines()

    entries: list[str] = []
    for line in lines:
        matches = BIB_ENTRY_RE.match(line)
        if matches:
            entries.append("")
        entries[-1] += line

    bib_entries: list[BibEntry] = []
    for entry in entries:
        e = entry.strip().splitlines()
        entrytype, citekey = BIB_ENTRY_RE.findall(e.pop(0))[0]

        content = {}
        for line in e:
            i_eq = line.find("=")
            if i_eq != -1:
                key = line[:i_eq].strip()
                val = line[i_eq+1:]
                leading_br = val.find("{")
                trailing_br = len(val)-val[::-1].find("}")
                content[key] = val[leading_br+1:trailing_br-1]
        
        if len(content) > 0:
            bib_entries.append(
                BibEntry(entrytype, citekey, content)
            )
        else:
            msg = f"Malformed entry ({citekey}) found in .bib file: {file}"
            click.secho(msg)

    return bib_entries


def bib_union(bibs: list[BibEntry], additional_bibs: list[BibEntry]):
    """Join two lists of .bib file entries, checking for duplicate keys.

    If the citekey exists in both lists, the title is checked. If the title
    is the same, it is assumed that the reference already exists in the main list,
    and is skipped silently. If the titles do not match, a warning is given.

    :param bibs: Main list of bib entries.
    :param additional_bibs: List of additional bib entries you want to add to 
        the main list.
    :return: Joined list of .bib file entries.
    """
    bib_citekeys = set(bib.citekey for bib in bibs)
    extra_citekeys = set(bib.citekey for bib in additional_bibs)
    overlap = bib_citekeys.intersection(extra_citekeys)

    if len(overlap) == 0:  # no overlap: clean join
        return bibs + additional_bibs

    merged_bibs = bibs.copy()
    for entry in additional_bibs:
        if entry.citekey not in overlap:
            merged_bibs.append(entry)
        else:  # citekey already exists. check if title is the same
            bib_title = find(entry.citekey, bibs).content["title"]
            if bib_title == entry.content["title"]:
                pass
            else:
                msg = (
                    f"Warning: Found duplicate citekey '{entry.citekey}'in bibfile.\n"
                    "    However, the titles did not match.\n"
                    "    References in external content might be incorrect!"
                )
                click.secho(msg, **CLICK_WARNING_KWARGS)

    return merged_bibs


def find(citekey: str, bibs: list[BibEntry]) -> BibEntry:
    """Find bib entry by citekey"""
    key_index = [bib.citekey == citekey for bib in bibs].index(True)
    return bibs[key_index]
