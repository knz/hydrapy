
.SUFFIXES: .html .tex .pdf .rst .sty

all: langif.html langif.pdf

RST2HTML = rst2html-2.7.py
RST2LATEX = rst2latex-2.7.py
HTMLDEFCSS = /opt/local/Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/site-packages/docutils/writers/html4css1/html4css1.css
PYGMENTIZE = pygmentize-2.7
PYTHON = python2.7

langif.html: langif.rst colorful-fruity.css
	$(RST2HTML) $< --stylesheet=$(HTMLDEFCSS),colorful-fruity.css >$@

colorful-fruity.css:
	$(PYGMENTIZE) -f html -S fruity >$@

langif.pdf: langif.tex colorful-default.sty
	rubber -d langif.tex

langif.tex: langif.rst
	$(RST2LATEX) $< --stylesheet=colorful-default.sty >$@

colorful-default.sty: makesty.py
	$(PYGMENTIZE) -f html -S default | $(PYTHON) makesty.py >colorful-default.sty