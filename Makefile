.PHONY: install api web test schema

install:
	cd backend && python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
	cd frontend && npm install

api:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

web:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/pytest -q

# Re-export the SDL after changing the Strawberry schema; the frontend codegen reads it.
schema:
	cd backend && .venv/bin/strawberry export-schema app.schema:schema > ../schema.graphql
