RST2HTML = rst2html-2.7.py
HTMLDEFCSS = /opt/local/Library/Frameworks/Python.framework/Versions/2.7/lib/python2.7/site-packages/docutils/writers/html4css1/html4css1.css
PYGMENTIZE = pygmentize-2.7

langif.html: langif.rst colorful-fruity.css
	$(RST2HTML) $< --stylesheet=$(HTMLDEFCSS),colorful-fruity.css >$@

colorful-fruity.css:
	pygmentize-2.7 -f html -S fruity >$@
