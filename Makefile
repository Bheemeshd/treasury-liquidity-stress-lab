PYTHON ?= python3
export PYTHONPATH := $(CURDIR)/src
export PYTHONPYCACHEPREFIX := /tmp/liquidity_stress_pycache

.PHONY: all data database analyze test check dashboard

all:
	$(PYTHON) scripts/run_pipeline.py

data:
	$(PYTHON) -m liquidity_stress.generate --output-dir data/raw --seed 20260902 --positions 900

database: data
	$(PYTHON) -m liquidity_stress.database --input-dir data/raw --database data/processed/liquidity_stress.db

analyze: database
	$(PYTHON) -m liquidity_stress.pipeline --database data/processed/liquidity_stress.db --output-dir outputs --artifact-dir artifacts

test:
	$(PYTHON) -m unittest discover -s tests -v

check: test
	$(PYTHON) -m compileall -q src app.py scripts tests

dashboard: all
	$(PYTHON) -m streamlit run app.py

