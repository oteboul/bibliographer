import os
import tornado.web

class CitationUI(tornado.web.UIModule):

    def render(self, citation, idx=None, count=-1):
        return self.render_string(
            "citation.html", citation=citation, idx=idx, count=count)

    def embedded_css(self):
        dirname = os.path.dirname(__file__)
        path = os.path.join(dirname, 'static/citation.css')
        with open(path) as fp:
            return fp.read()