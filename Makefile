.PHONY: run test eval install lint

install:
	pip install -e ".[dev]"

run:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

test:
	python -m pytest tests/ -v

eval:
	python scripts/run_evals.py --mode code --cases all

lint:
	python -m py_compile config.py
	python -m py_compile services/llm_client.py
	python -m py_compile orchestration/code_orchestrator.py
