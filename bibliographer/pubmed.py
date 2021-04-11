"""A Parser for PubMed articles.

This module needs the chromedriver, which must be and have it in the system 
path.
"""

import os
import re
import logging
from typing import Any, List, Optional
import urllib.parse

import lxml
import lxml.html
import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from bibliographer import citation


def to_url(pmid: str):
    return f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/'


class PubmedFetcher:
    """Fetches and parses PubMed HTML."""

    def __init__(self):
        self._browser = webdriver.Chrome()

    def stop(self):
        self._browser.close()

    @staticmethod
    def matches(url: str) -> bool:
        return 'pubmed.ncbi.nlm.nih.gov' in url

    async def fetch(self, url: str) -> str:
        """Clicks on show all references and returns full html"""
        # TODO(oliviert): migrate to arsenic
        logging.info(f'Fetching: {url}')
        self._browser.get(url)
        try:
            button = self._browser.find_element_by_xpath(
                '//*[@id="top-references-list"]/div/div/button')
            button.click()
            condition = EC.presence_of_element_located(
                (By.XPATH, '//*[@id="top-references-list-1"]/li[6]/ol/li'))
            WebDriverWait(self._browser, 10).until(condition)
        except selenium.common.exceptions.NoSuchElementException as e:
            logging.error(f'{url} has no references.')
        return self._browser.page_source

    def parse(self, html: str) -> citation.Citation:
        """Parse a page from PubMed and returns a Citation."""
        etree = lxml.html.fromstring(html)
        result = citation.Citation()

        result.title = etree.xpath('//h1[@class="heading-title"]/text()')[0].strip()
        result.authors = etree.xpath('//div[@class="inline-authors"]//span[@class="authors-list-item"]/a/text()')
        if not result.authors:
            result.authors = etree.xpath('//div[@class="inline-authors"]//span[@class="authors-list-item "]/a/text()')

        abstract = etree.xpath("//div[@class='abstract']/div/p")
        if abstract:
            result.abstract = abstract[0].text_content().strip()

        result.pmid = etree.xpath('//span[@class="identifier pubmed"]/strong/text()')[0].strip()
        pmcid = etree.xpath('//span[@class="identifier pmc"]/a')
        if pmcid:
            result.pmcid = pmcid[0].text.strip() if pmcid else ''
            result.pmc_url = pmcid[0].attrib['href']
        result.journal = etree.xpath('//*[@id="full-view-journal-trigger"]/text()')[0].strip()
        year_volume = etree.xpath(
            '//*[@class="article-source"]/span[@class="cit"]/text()')[0].split(';')
        if len(year_volume) > 1:
            result.year, result.volume = year_volume
        else:
            parts = year_volume[0].split()
            result.year = parts[0]
            result.volume = ' '.join(parts[1:])

        cited_by_elems = etree.xpath('//*[@id="citedby-articles-list"]/li/div')
        for elem in cited_by_elems:
            curr = citation.Citation()
            title = elem.xpath('.//a[@class="docsum-title"]')[0]
            curr.title = title.text.strip()
            curr.pm_url = title.attrib['href']
            if curr.pm_url.startswith('/'):
                curr.pm_url = f'https://pubmed.ncbi.nlm.nih.gov{curr.pm_url}'
            authors = elem.xpath(
                './/span[@class="docsum-authors full-authors"]/text()')
            curr.authors = authors[0].strip().split(', ')
            curr.pmid = elem.xpath(
                './/span[@class="docsum-pmid"]/text()')[0].strip()
            result.cited_by.append(curr)

        references = etree.xpath('//div[@id="references"]//ol[@class="references-list"]//li[@class="skip-numbering"]')
        for elem in references:
            curr = citation.Citation()
            ref = elem.text.strip().strip('-').strip()
            regex = r'([\w\.,\s]+)\s\(([0-9]+)\)\.\s(.*)'
            match = re.search(regex, ref)
            if match is not None:
                curr.authors = match.group(1).split(', ')
                curr.year = match.group(2)
                curr.title = match.group(3)
            else:
                curr.title = ref

            links = {a.text.strip(): a.attrib['href']
                    for a in elem.xpath('.//a[@class="reference-link"]')}

            link = links.get('PMC', None)
            if link is not None:
                curr.pmcid = link.strip('/').split('/')[-1]
                curr.pmc_url = f'https://www.ncbi.nlm.nih.gov/pmc/articles/{curr.pmcid}/'
            link = links.get('PubMed', None)
            if link is not None:
                curr.pmid = link.strip('/').split('/')[-1]
                curr.pm_url = f'https://pubmed.ncbi.nlm.nih.gov/{curr.pmid}/'
            result.references.append(curr)
        return result
        