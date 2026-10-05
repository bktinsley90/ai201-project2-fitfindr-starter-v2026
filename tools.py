"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively at a whole-token boundary —
                     "M" matches "S/M", but "L" does not match "XL".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap across listing text and tags.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    def words(value: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", value.casefold())

    query_words = set(words(description))
    requested_size = words(size) if size else []
    scored_listings = []

    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue

        listing_size_words = words(str(listing.get("size", "")))
        listing_words = words(" ".join(
            str(value)
            for value in (
                listing.get("title", ""),
                listing.get("description", ""),
                listing.get("category", ""),
                " ".join(listing.get("style_tags", [])),
                " ".join(listing.get("colors", [])),
                listing.get("brand") or "",
            )
        ))

        if requested_size and not any(
            listing_size_words[index:index + len(requested_size)] == requested_size
            for index in range(len(listing_size_words) - len(requested_size) + 1)
        ):
            continue

        score = len(query_words.intersection(listing_words))
        if score:
            scored_listings.append((score, listing))

    scored_listings.sort(key=lambda result: result[0], reverse=True)
    return [
        listing
        for _, listing in scored_listings[:config.SEARCH_RESULT_LIMIT]
    ]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    wardrobe_items = wardrobe.get("items", [])
    item_details = "\n".join(
        f"- {label}: {value}"
        for label, value in (
            ("Name", new_item.get("title", "Unspecified item")),
            ("Description", new_item.get("description", "")),
            ("Category", new_item.get("category", "")),
            ("Size", new_item.get("size", "")),
            ("Condition", new_item.get("condition", "")),
            ("Colors", ", ".join(new_item.get("colors", []))),
            ("Style tags", ", ".join(new_item.get("style_tags", []))),
        )
        if value
    )

    if wardrobe_items:
        wardrobe_details = "\n".join(
            f"- {item.get('name', 'Unnamed item')} "
            f"(category: {item.get('category', 'unspecified')}; "
            f"colors: {', '.join(item.get('colors') or []) or 'unspecified'}; "
            f"style: {', '.join(item.get('style_tags') or []) or 'unspecified'}"
            f"{'; notes: ' + str(item['notes']) if item.get('notes') else ''})"
            for item in wardrobe_items
        )
        prompt = (
            f"Suggest one or two wearable outfits featuring this thrift find.\n\n"
            f"New item:\n{item_details}\n\n"
            f"The user's wardrobe:\n{wardrobe_details}\n\n"
            "Use specific pieces from the wardrobe and name them as listed. "
            "Do not claim the user owns anything not in the wardrobe. "
            "Briefly explain how the pieces work together."
        )
        system = (
            "You are a practical personal stylist. Make suggestions specific "
            "to the item and the provided wardrobe."
        )
    else:
        prompt = (
            f"Give one or two general outfit ideas for styling this thrift find. "
            "The user has not provided a wardrobe, so do not imply they own "
            "specific pieces. Suggest versatile kinds of items they could pair "
            f"with it.\n\nNew item:\n{item_details}"
        )
        system = (
            "You are a practical personal stylist. Give concise, specific "
            "styling advice without assuming what the user owns."
        )

    suggestion = generate(prompt, system=system)
    if not suggestion.strip():
        raise RuntimeError("The model returned an empty outfit suggestion.")
    return suggestion


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit.strip():
        title = new_item.get("title") or "This thrift find"
        price = new_item.get("price")
        platform = new_item.get("platform")
        details = []
        if price is not None:
            details.append(f"${price}")
        if platform:
            details.append(f"on {platform}")
        suffix = f" ({' '.join(details)})" if details else ""
        return f"{title}{suffix} is ready for its next great outfit."

    item_details = "\n".join(
        f"- {label}: {value}"
        for label, value in (
            ("Title", new_item.get("title", "")),
            ("Description", new_item.get("description", "")),
            ("Category", new_item.get("category", "")),
            ("Price", f"${new_item['price']}" if new_item.get("price") is not None else ""),
            ("Platform", new_item.get("platform", "")),
            ("Colors", ", ".join(new_item.get("colors", []))),
            ("Style tags", ", ".join(new_item.get("style_tags", []))),
        )
        if value
    )
    prompt = (
        "Write a natural, social-media-style fit-card caption in 2-4 sentences. "
        "Make the vibe specific to the item and outfit, not a generic product "
        "description. Mention the item's exact title, price, and platform "
        "exactly once each. Do not invent item details.\n\n"
        f"Item:\n{item_details}\n\n"
        f"Suggested outfit:\n{outfit.strip()}"
    )
    system = (
        "You write concise, authentic thrift-fashion captions. Follow the "
        "requested sentence count and include the required item details."
    )
    caption = generate(prompt, system=system)
    if not caption.strip():
        raise RuntimeError("The model returned an empty fit-card caption.")
    return caption
