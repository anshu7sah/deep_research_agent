import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Settings
from evals.runner import EvalRunner
from logging_config import setup_logging


async def main():
    parser = argparse.ArgumentParser(description="Run deep research evaluations")
    parser.add_argument("--mode", choices=["code", "llm"], default="code")
    parser.add_argument("--cases", default="all")
    args = parser.parse_args()

    setup_logging("INFO")
    settings = Settings()
    runner = EvalRunner(settings)

    cases_path = None
    if args.cases != "all":
        cases_path = args.cases

    results = await runner.run_all(args.mode, cases_path)

    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.case_id} ({r.duration_seconds}s)")
        if r.metrics:
            for k, v in r.metrics.items():
                print(f"         {k}: {v:.3f}")
        if r.error:
            print(f"         ERROR: {r.error}")

    passed = sum(1 for r in results if r.passed)
    print(f"\nTotal: {passed}/{len(results)} passed")


if __name__ == "__main__":
    asyncio.run(main())
