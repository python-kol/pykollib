import re
from typing import Optional
from copy import copy
from itertools import groupby
from dataclasses import dataclass
from typing import Any, Dict, List

from bs4 import BeautifulSoup, Tag

import libkol

from .. import types
from ..pattern import PatternManager
from ..Stat import Stat


def panel(html: str, title: str = "Results:") -> Tag:
    soup = BeautifulSoup(html, "html.parser")
    headers = soup.find_all("b", text=title)
    header = next(h for h in headers)
    return header.parent.parent.next_sibling.td


def get_value(soup: Tag, key: str) -> Optional[Tag]:
    for k in soup.find_all("td", align="right"):
        if k.get_text() == f"{key}:":
            return k.next_sibling
    return None


def to_float(s: str) -> float:
    return float(s.replace(",", "").strip())


def to_int(s: str) -> int:
    return int(s.replace(",", "").strip())


def wrap_elements(wrapper: Tag, elements: List[Tag]):
    w = copy(wrapper)
    elements[0].wrap(w)
    for e in elements[1:]:
        w.append(e)
    return w


def split_by_br(element: Tag, wrapper: Tag = None):
    elements = [
        g
        for g in (
            list(g) for k, g in groupby(element.children, key=lambda e: e.name != "br")
        )
        if g[0].name != "br"
    ]

    return (
        elements if wrapper is None else [wrap_elements(wrapper, e) for e in elements]
    )


single_item_pattern = re.compile(
    r"<td[^>]*><img src=\"[^\"]*\" alt=\"[^\"]*\" title=\"[^\"]*\"[^>]*descitem\(([0-9]+)\)[^>]*><\/td><td[^>]*>You acquire an item"
)
multi_item_pattern = re.compile(
    r"<td[^>]*><img src=\"[^\"]*\" alt=\"[^\"]*\" title=\"[^\"]*\"[^>]*descitem\(([0-9]+)\)[^>]*><\/td><td[^>]*>You acquire <b>([0-9,]*)"
)

gain_meat_pattern = re.compile(
    r"<td><img src=\"[^\"]*meat\.gif\"[^>]*><\/td><td[^>]*>You gain ([0-9,]*?) Meat\.<\/td>"
)
lose_meat_pattern = re.compile(r"You (?:lose|spent) ([0-9,]+) Meat")


async def item(text: str) -> List["types.ItemQuantity"]:
    from .. import Item

    item_quantities = []  # type: List[types.ItemQuantity]

    for match in single_item_pattern.finditer(text):
        item = await Item.get_or_discover(desc_id=int(match.group(1)))
        item_quantities += [types.ItemQuantity(item, 1)]

    for match in multi_item_pattern.finditer(text):
        quantity = to_int(match.group(2))
        item = await Item.get_or_discover(desc_id=int(match.group(1)))
        item_quantities += [types.ItemQuantity(item, quantity)]

    return item_quantities


def meat(text) -> int:
    match = gain_meat_pattern.search(text)
    if match:
        return int(match.group(1).replace(",", ""))

    match = lose_meat_pattern.search(text)
    if match:
        return -1 * int(match.group(1).replace(",", ""))

    return 0


def substat(text: str, stat: Stat = None) -> Dict[str, int]:
    substats = {}

    if stat in [Stat.Muscle, None]:
        muscPattern = PatternManager.getOrCompilePattern("muscleGainLoss")
        muscMatch = muscPattern.search(text)
        if muscMatch:
            muscle = int(muscMatch.group(2).replace(",", ""))
            substats["muscle"] = muscle * (1 if muscMatch.group(1) == "gain" else -1)

    if stat in [Stat.Mysticality, None]:
        mystPattern = PatternManager.getOrCompilePattern("mysticalityGainLoss")
        mystMatch = mystPattern.search(text)
        if mystMatch:
            myst = int(mystMatch.group(2).replace(",", ""))
            substats["mysticality"] = myst * (1 if mystMatch.group(1) == "gain" else -1)

    if stat in [Stat.Moxie, None]:
        moxPattern = PatternManager.getOrCompilePattern("moxieGainLoss")
        moxMatch = moxPattern.search(text)
        if moxMatch:
            moxie = int(moxMatch.group(2).replace(",", ""))
            substats["moxie"] = moxie * (1 if moxMatch.group(1) == "gain" else -1)

    return substats


def stats(text: str, stat: Stat = None) -> Dict[Stat, int]:
    """
    Returns a dictionary describing how many stat points the user gained or lost. Please note that
    the user interface does not say how many points were gained or lost if the number is greater
    than 1. This method will return '2' or '-2' in these situations. If your program needs a more
    exact number then you should request the user's character pane.
    """
    statPoints = {}

    if stat in [Stat.Muscle, None]:
        muscPattern = PatternManager.getOrCompilePattern("musclePointGainLoss")
        muscMatch = muscPattern.search(text)
        if muscMatch:
            modifier = 1
            if muscMatch.group(1) == "lose":
                modifier = -1
            if muscMatch.group(2) == "a":
                statPoints[Stat.Muscle] = 1 * modifier
            else:
                statPoints[Stat.Muscle] = 2 * modifier

    if stat in [Stat.Mysticality, None]:
        mystPattern = PatternManager.getOrCompilePattern("mystPointGainLoss")
        mystMatch = mystPattern.search(text)
        if mystMatch:
            modifier = 1
            if mystMatch.group(1) == "lose":
                modifier = -1
            if mystMatch.group(2) == "a":
                statPoints[Stat.Mysticality] = 1 * modifier
            else:
                statPoints[Stat.Mysticality] = 2 * modifier

    if stat in [Stat.Moxie, None]:
        moxPattern = PatternManager.getOrCompilePattern("moxiePointGainLoss")
        moxMatch = moxPattern.search(text)
        if moxMatch:
            modifier = 1
            if moxMatch.group(1) == "lose":
                modifier = -1
            if moxMatch.group(2) == "a":
                statPoints[Stat.Moxie] = 1 * modifier
            else:
                statPoints[Stat.Moxie] = 2 * modifier

    return statPoints


def level(text: str) -> int:
    """
    Returns the number of levels gained by the user during the request. Please note that the user
    interface does not say how many levels were gained if the user gained more than 1. This method
    will return 2 if more than 1 level was gained. If your application needs a more fine-grained
    response, you should check the user's character pane.
    """
    levelPattern = PatternManager.getOrCompilePattern("levelGain")
    levelMatch = levelPattern.search(text)
    if levelMatch is None:
        return 0

    return 1 if levelMatch.group(1) == "a" else 2


def hp(text: str) -> int:
    hp = 0
    hpPattern = PatternManager.getOrCompilePattern("hpGainLoss")
    # Need to do an iteration because it may happen multiple times in combat.
    for hpMatch in hpPattern.finditer(text):
        hpChange = int(hpMatch.group(2).replace(",", ""))
        hp += hpChange * (1 if hpMatch.group(1) == "gain" else -1)

    return hp


def mp(text: str) -> int:
    mp = 0
    mpPattern = PatternManager.getOrCompilePattern("mpGainLoss")
    # Need to do an iteration because it may happen multiple times in combat
    for mpMatch in mpPattern.finditer(text):
        mpChange = int(mpMatch.group(2).replace(",", ""))
        mp += mpChange * (1 if mpMatch.group(1) == "gain" else -1)

    return mp


def inebriety(text: str) -> int:
    drunkPattern = PatternManager.getOrCompilePattern("gainDrunk")
    match = drunkPattern.search(text)
    return int(match.group(1).replace(",", "")) if match else 0


def adventures(text: str) -> int:
    adventurePattern = PatternManager.getOrCompilePattern("gainAdventures")
    match = adventurePattern.search(text)
    return int(match.group(1).replace(",", "")) if match else 0


def effects(text: str) -> List[Dict[str, Any]]:
    effects = []  # type: List[Dict[str, Any]]
    effectPattern = PatternManager.getOrCompilePattern("gainEffect")
    for match in effectPattern.finditer(text):
        effects += [
            {"name": match.group(1), "turns": int(match.group(2).replace(",", ""))}
        ]

    return effects


@dataclass
class ResourceGain:
    items: List["types.ItemQuantity"]
    adventures: int
    inebriety: int
    substats: Dict[str, int]
    stats: Dict[Stat, int]
    levels: int
    effects: List[Dict[str, Any]]
    hp: int
    mp: int
    meat: int


async def resource_gain(
    html: str, session: Optional["libkol.Session"] = None
) -> ResourceGain:
    rg = ResourceGain(
        items=(await item(html)),
        adventures=adventures(html),
        inebriety=inebriety(html),
        substats=substat(html),
        stats=stats(html),
        levels=level(html),
        effects=effects(html),
        hp=hp(html),
        mp=mp(html),
        meat=meat(html),
    )

    if session:
        for iq in rg.items:
            session.state.inventory[iq.item] += iq.quantity
        session.state.adventures += rg.adventures
        session.state.inebriety += rg.inebriety

        for stat, change in rg.stats.items():
            session.state.stats[stat].base += change
            session.state.stats[stat].buffed += change

        session.state.level += rg.levels

        for effect in rg.effects:
            session.state.effects[effect["name"]] = (
                session.state.effects.get(effect["name"], 0) + effect["turns"]
            )

        session.state.meat += rg.meat

        session.state.current_hp += rg.hp
        session.state.current_mp += rg.mp

    return rg
