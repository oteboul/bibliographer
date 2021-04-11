"""A parser for PMC articles."""

import os
import logging
import urllib.parse

import lxml
import lxml.html

import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from bibliographer import citation


class PMCFetcher:
    """Fetches and parses PMC HTML."""

    URL_PREFIX = 'www.ncbi.nlm.nih.gov/pmc/articles'

    def __init__(self):
        self._browser = webdriver.Chrome()

    def stop(self):
        self._browser.close()

    @classmethod
    def matches(cls, url: str) -> bool:
        return cls.URL_PREFIX in url

    async def fetch(self, url: str) -> str:
        logging.info(f'Fetching: {url}')
        self._browser.get(url)
        condition = EC.presence_of_element_located(
                (By.XPATH, '//*[@class="content-title"]'))
        WebDriverWait(self._browser, 10).until(condition)
        return self._browser.page_source

    def get_edition(self, etree):
        edition = etree.xpath(
            '//div[@class="citation-default"]/div[@class="part1"]')
        if edition:
            edition = edition[0]
        else:
            edition = etree.xpath('//*[@class="fm-citation"]/*/span')[0]

        journal = edition.getchildren()[0].text_content()
        year_volume = edition.getchildren()[0].tail
        if not year_volume:
            year_volume = etree.xpath('//*[@class="fm-vol-iss-date"]/a/text()')
            if year_volume:
                year_volume = year_volume[0][len(journal) + 1:]

        year, volume = year_volume.strip().split('; ')
        return journal, year, volume


    def parse(self, html: str) -> citation.Citation:
        """Parses an HTML from PMC into a Citation entry."""
        result = citation.Citation()
        etree = lxml.html.fromstring(html)
        result.title = etree.xpath('//*[@class="content-title"]/text()')[0]
        result.journal, result.year, result.volume = self.get_edition(etree)
        result.pmid = etree.xpath('//*[@class="fm-citation-pmid"]/*/text()')[0]
        result.pmcid = etree.xpath('//*[@class="fm-citation-pmcid"]/span/text()')[-1]
        result.authors = etree.xpath('//div[@class="contrib-group fm-author"]/a/text()')
        result.affiliations = etree.xpath('//div[@class="fm-affl"]/text()')

        # For abstract finds the abstract h2 first.
        h2s = etree.xpath('//h2')
        for h2 in h2s:
            texts = h2.xpath('text()')
            if texts and texts[0] == 'Abstract':
                abstract = h2.getparent().xpath('div/p')
                if abstract:
                    result.abstract = abstract[0].text_content()

        refs = etree.xpath('//li/span[@class="mixed-citation"]')
        for ref in refs:
            links = {x.text: x.attrib['href'] for x in ref.xpath('.//a')}
            curr = citation.Citation()

            google_url = links.get('Google Scholar', None)
            if google_url is not None:
                info = urllib.parse.parse_qs(urllib.parse.urlparse(google_url).query)
                curr.title = info.get('title', [""])[0]
                curr.authors = info.get('author', [])
                curr.year = info.get('publication_year', [""])[0]

            pubmed_url = links.get('PubMed', None)
            if pubmed_url is not None:
                curr.pmid = os.path.split(pubmed_url.rstrip('/'))[1]
                curr.pm_url = f'https://pubmed.ncbi.nlm.nih.gov/{curr.pmid}'
                
            pmc_url = links.get('PMC free article', None)
            if pmc_url is not None:
                curr.pmcid = os.path.split(pmc_url.rstrip('/'))[1]
                curr.pmc_url = f'https://{self.URL_PREFIX}/{curr.pmcid}/'

            result.references.append(curr)

        return result