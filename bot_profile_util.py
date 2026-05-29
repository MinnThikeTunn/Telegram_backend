import asyncio
from telegram import Bot


async def update_bot_name(token: str, name: str) -> bool:
    """Update bot display name."""
    async with Bot(token=token) as bot:
        await bot.set_my_name(name=name)
    return True


async def update_bot_short_description(token: str, short_description: str) -> bool:
    """Update bot short description."""
    async with Bot(token=token) as bot:
        await bot.set_my_short_description(short_description=short_description)
    return True


async def update_bot_description(token: str, description: str) -> bool:
    """Update bot description."""
    async with Bot(token=token) as bot:
        await bot.set_my_description(description=description)
    return True


async def update_bot_profile(
    token: str,
    name: str | None = None,
    short_description: str | None = None,
    description: str | None = None,
) -> dict:
    """Update bot profile with optional fields."""
    results = {}

    if name:
        await update_bot_name(token, name)
        results["name"] = "updated"

    if short_description:
        await update_bot_short_description(token, short_description)
        results["short_description"] = "updated"

    if description:
        await update_bot_description(token, description)
        results["description"] = "updated"

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Update Telegram bot profile")
    parser.add_argument("--token", required=True, help="Bot token")
    parser.add_argument("--name", help="Bot display name")
    parser.add_argument("--short-description", help="Bot short description")
    parser.add_argument("--description", help="Bot description")
    args = parser.parse_args()

    results = asyncio.run(
        update_bot_profile(
            token=args.token,
            name=args.name,
            short_description=args.short_description,
            description=args.description,
        )
    )
    print(results)


if __name__ == "__main__":
    main()