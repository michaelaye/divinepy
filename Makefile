.ONESHELL:
SHELL := /bin/bash
SRC = $(wildcard ./*.ipynb)

all: divinepy docs

divinepy: $(SRC)
	nbdev_build_lib
	touch divinepy

sync:
	nbdev_update_lib

docs_serve: docs
	cd docs && bundle exec jekyll serve

docs: $(SRC)
	nbdev_build_docs
	touch docs

test:
	nbdev_test_nbs

release: pypi
	sleep 5
	fastrelease_conda_package --mambabuild --upload_user michaelaye && fastrelease_bump_version

pypi: dist
	twine upload --repository pypi dist/*

dist: clean
	python setup.py sdist bdist_wheel

clean:
	rm -rf dist
