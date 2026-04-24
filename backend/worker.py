import asyncio

from app.workers.collector import run_collector_loop
from app.workers.macro import run_macro_loop


async def main() -> None:
    await asyncio.gather(run_collector_loop(), run_macro_loop())


if __name__ == "__main__":
    asyncio.run(main())
