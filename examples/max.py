import os
from dotenv import load_dotenv
from libkol import Session, run, Modifier, Maximizer, Item

load_dotenv()


async def main():
    async with Session() as kol:
        await kol.login(os.getenv("KOL_USERNAME"), os.getenv("KOL_PASSWORD"))
        problem = Maximizer(kol)
        problem += Modifier.HotResistance
        problem += await Item["high-temperature mining drill"]

        try:
            items, familiar, throne_familiars = await problem.solve()

            if familiar:
                print(f"Familiar: {familiar.name}")

            for f in throne_familiars:
                print(f"Enthrone: {f.name}")

            for slot, i in items.items():
                print(f"{slot.value}: {i.name}")
        except ValueError as e:
            print(f"Not possible ({e})")


if __name__ == "__main__":
    run(main)
