"""Defines a citation object."""

from typing import List
import dataclasses


@dataclasses.dataclass
class Citation:
    """A Citation is a bibliography entry."""
    pmid: str = ""
    pmcid: str = ""
    pm_url: str = ""
    pmc_url: str = ""
    title: str = ""
    abstract: str = ""
    authors: List[str] = ""
    year: str = ""
    journal: str = ""
    volume: str = ""
    depth: int = -1
    affiliations: str = ""
    references: List['Citation'] = dataclasses.field(default_factory= lambda: [])
    cited_by: List['Citation'] = dataclasses.field(default_factory= lambda: [])
    title_fr: str = ""
    abstract_fr: str = ""