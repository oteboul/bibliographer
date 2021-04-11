import collections
import functools
import logging

from bibliographer import google_api


class CitationAggregator:
    """Finds the articles with biggest number of citations."""

    def __init__(self, db):
        self._db = db
        self._articles = {}
        for url, citation in db.items():
            if citation is None or not citation.pmid:
                continue

            if not citation.pm_url:
                citation.pm_url = url
            self._articles[citation.pmid] = citation
            self._db[url] = citation

    def __len__(self):
        return len(self._articles)

    def may_translate(self, citation):
        to_fr = functools.partial(google_api.translate, target='fr')
        has_changed = False
        if citation.abstract and not citation.abstract_fr:
            logging.info('Fetch translations.')
            citation.abstract_fr = to_fr(citation.abstract)
            has_changed = True
        if citation.title and not citation.title_fr:
            logging.info('Fetch translations.')
            citation.title_fr = to_fr(citation.title)
            has_changed = True

        if has_changed:
            logging.info(f'Saving back to shelve DB.')
            self._articles[citation.pmid] = citation
            self._db[citation.pm_url] = citation        

    def most_cited(self, k: int = 10):
        counts = collections.Counter()
        for ref in self._articles.values():
            if ref is None:
                continue
            pmids = [r.pmid for r in ref.references if r.pmid != '']
            if pmids:
                counts.update(pmids)
        topk = counts.most_common(k)
        result = [(self._articles[v[0]], v[1])
                  for v in topk if v[0] in self._articles]
        for citation, _ in result:
            self.may_translate(citation)
        return result
        