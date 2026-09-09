PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
NPM ?= npm
MKDOCS ?= mkdocs

.PHONY: help setup npm-install serve build package test test-py test-js test-browser test-all clean

help:
	@printf '%s\n' \
		'Targets:' \
		'  make setup         Install Python package in editable mode with test extras' \
		'  make npm-install   Install Node/browser test dependencies' \
		'  make serve         Run the example MkDocs site locally' \
		'  make build         Build the example MkDocs site in strict mode' \
		'  make package       Build the Python package' \
		'  make test          Run Python and JavaScript unit tests' \
		'  make test-py       Run Python tests' \
		'  make test-js       Run JavaScript unit tests' \
		'  make test-browser  Build the example site and run browser smoke test' \
		'  make test-all      Run all tests, including browser smoke test' \
		'  make clean         Remove generated build/site artifacts'

setup:
	$(PIP) install -e '.[test]'

npm-install:
	$(NPM) install

serve:
	$(MKDOCS) serve -f example/mkdocs.yml

build:
	$(MKDOCS) build -f example/mkdocs.yml --strict

package:
	$(PYTHON) -m build

test: test-py test-js

test-py:
	$(PYTHON) -m pytest -q

test-js:
	$(NPM) test

test-browser: build
	$(NPM) run test:browser

test-all: test build test-browser

clean:
	rm -rf build dist *.egg-info example/site
