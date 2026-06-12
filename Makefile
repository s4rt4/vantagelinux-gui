.PHONY: install uninstall deps run

PREFIX  ?= /usr
DESTDIR ?=
APPDIR   = $(DESTDIR)$(PREFIX)/share/vantage
BINDIR   = $(DESTDIR)$(PREFIX)/bin
ICONDIR  = $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps
DESKDIR  = $(DESTDIR)$(PREFIX)/share/applications

# Install runtime dependencies via the distro package manager.
deps:
	chmod +x ./install.sh
	./install.sh

# Run straight from the source tree, no install needed.
run:
	python3 vantage.py

install: deps
	# application code + assets
	install -d $(APPDIR)
	cp -r vantage_gui assets vantage.py $(APPDIR)/
	# launcher on PATH
	install -d $(BINDIR)
	printf '#!/bin/sh\nexec python3 $(PREFIX)/share/vantage/vantage.py "$$@"\n' > $(BINDIR)/vantage
	chmod a+rx $(BINDIR)/vantage
	# icon (the Tux-on-Lenovo-red logo) + desktop entry
	install -Dm644 assets/icons/logo.svg $(ICONDIR)/vantage.svg
	install -Dm644 vantage.desktop $(DESKDIR)/vantage.desktop

uninstall:
	rm -rf $(APPDIR)
	rm -f $(BINDIR)/vantage
	rm -f $(ICONDIR)/vantage.svg
	rm -f $(DESKDIR)/vantage.desktop
