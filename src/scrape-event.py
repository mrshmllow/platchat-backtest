# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "beautifulsoup4",
#   "python-dateutil"
# ]
# ///

from typing import Literal
from enum import Enum
from dateutil import parser
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import csv
from dataclasses import dataclass, field, asdict
from datetime import UTC, datetime, timedelta
import os.path

import ssl

ssl._create_default_https_context = ssl._create_unverified_context

PLATCHAT_GUARANTEE = 500
NORMAL_PRED = 100

TAGS = {
    "Natus Vincere": "NAVI",
    "Team Vitality": "VIT",
    "FUT Esports": "FUT",
    "Team Liquid": "TL",
    "Team Heretics": "TH",
    "FNATIC": "FNC",
    "Apeks": "APK",
    "GIANTX": "GX",
    "Gentle Mates": "M8",
    "KOI": "KOI",
    "Cloud9": "C9",
    "LEVIATÁN": "LEV",
    "Evil Geniuses": "EG",
    "MIBR": "MIBR",
    "100 Thieves": "100T",
    "Sentinels": "SEN",
    "2Game Esports": "2G",
    "FURIA": "FUR",
    "NRG": "NRG",
    "G2 Esports": "G2",
    "LOUD": "LOUD",
    "BBL Esports": "BBL",
    "Karmine Corp": "KC",
    "KRÜ Esports": "KRU",
    "T1": "T1",
    "DRX": "DRX",
    "ZETA DIVISION": "ZETA",
    "DRX": "DRX",
    "BOOM Esports": "BOOM",
    "Global Esports": "GE",
    "Paper Rex": "PRX",
    "TALON": "TLN",
    "Rex Regum Qeon": "RRQ",
    "Gen.G": "GENG",
    "Nongshim RedForce": "NS",
    "DetonatioN FocusMe": "DFM",
    "Team Secret": "TS",
}


class Team(Enum):
    A = "A"
    B = "B"
    Unknown = "Unknown"

    def opposite(self):
        if self == Team.Unknown:
            return self

        if self == Team.A:
            return Team.B

        return Team.A

    def __str__(self):
        return self.value


class Prediction(Enum):
    A = "A"
    B = "B"
    A_Guarantee = "AG"
    B_Guarantee = "BG"
    Split = "Split"
    Unknown = "Unknown"

    def is_guarantee(self):
        return self == Prediction.A_Guarantee or self == Prediction.B_Guarantee

    def is_team(self, team: Team):
        if self == Prediction.A or self == Prediction.A_Guarantee:
            return team == Team.A
        if self == Prediction.B or self == Prediction.B_Guarantee:
            return team == Team.B

        return False

    def __str__(self):
        return self.value


@dataclass
class Match:
    url: str

    team_a_name: str
    team_a_odds: float

    team_b_name: str
    team_b_odds: float

    recorded_date: str

    # "Unknown", "A", "B", "AG", "BG", "Split"
    pred: Prediction
    # "Unknown", "A", "B"
    winner: Team

    bet: int = field(init=False)
    winnings: float = field(init=False)

    date: str

    def __post_init__(self):
        if self.pred == Prediction.Split or self.pred == Prediction.Unknown:
            self.bet = 0
        elif self.pred.is_guarantee():
            self.bet = PLATCHAT_GUARANTEE
        else:
            self.bet = NORMAL_PRED

        self.calculate_winnings()

        if self.team_a_name in TAGS:
            self.team_a_name = TAGS[self.team_a_name]

        if self.team_b_name in TAGS:
            self.team_b_name = TAGS[self.team_b_name]

    def calculate_winnings(self):
        self.winnings = 0

        if self.winner == Team.Unknown:
            return

        odds = self.team_a_odds if self.winner == Team.A else self.team_b_odds

        if self.pred.is_team(self.winner):
            self.winnings = self.bet * odds
        else:
            self.winnings = 0

    def update_winner(self):
        req = Request(self.url)
        opened = urlopen(req)

        print(opened.getcode())

        html_page = opened.read()

        soup = BeautifulSoup(html_page, "html.parser")
        match_bet = soup.select(
            "div.match-header-vs-score > div.match-header-vs-score > div.js-spoiler"
        )
        winner_loser_spans = match_bet[0].select("span")
        team_a = winner_loser_spans[0].attrs.get("class")
        team_b = winner_loser_spans[2].attrs.get("class")

        if team_a == ["match-header-vs-score-winner"]:
            self.winner = Team.A
            return

        if team_b == ["match-header-vs-score-winner"]:
            self.winner = Team.B
            return

        print("Team had neither a winner nor loser?!")
        print(team_a, team_b)
        exit()


def get_matches(stage_id: str) -> list[str]:
    URL = f"https://www.vlr.gg/event/matches/{stage_id}/?series_id=all"

    req = Request(URL)
    html_page = urlopen(req).read()

    soup = BeautifulSoup(html_page, "html.parser")

    matches = [
        f"https://www.vlr.gg/{str(match.attrs.get("href"))[1:]}"
        for match in soup.select("a.match-item")
    ]

    return matches


def get_odds(match_url: str):
    req = Request(match_url)
    now = datetime.now()
    opened = urlopen(req)

    print(opened.getcode())

    html_page = opened.read()

    soup = BeautifulSoup(html_page, "html.parser")
    match_bet = soup.select("a.match-bet-item")

    if len(match_bet) > 1:
        print(match_url, "has more than 1 `a.match-bet-item`. ????")
        exit()

    print(match_url, len(soup.select("div.mod-pending")), len(match_bet))

    if len(soup.select("div.mod-pending")) != 0 or len(match_bet) != 1:
        print("skipping", match_url, "no odds found or match concluded")
        return None

    if len(match_bet[0].select("span.match-bet-item-team")) != 2:
        print("skipping", match_url, "match concluded")
        return None

    team_a_name, team_b_name = [
        team.string for team in match_bet[0].select("span.match-bet-item-team")
    ]
    team_a_odds, team_b_odds = [
        team.string for team in match_bet[0].select("span.match-bet-item-odds")
    ]

    date_elem = soup.select_one("div.moment-tz-convert")

    if date_elem is None:
        print(match_url, "No date found?!")
        return None

    date = date_elem.attrs.get("data-utc-ts")

    if date is None:
        print(match_url, "No date attribute found?!")
        return None

    print(date)

    return Match(
        url=match_url,
        team_a_name=str(team_a_name),
        team_a_odds=float(str(team_a_odds)),
        team_b_name=str(team_b_name),
        team_b_odds=float(str(team_b_odds)),
        recorded_date=now.strftime("%m/%d/%Y, %H:%M:%S"),
        pred=Prediction.Unknown,
        winner=Team.Unknown,
        date=str(date),
    )


def read_match_csv(match_id: str) -> list[Match]:
    FILE = f"{match_id}.csv"
    matches = []

    if not os.path.isfile(FILE):
        return matches

    with open(FILE, newline="") as csvfile:
        reader = csv.DictReader(csvfile, dialect="excel-tab")

        for row in reader:
            matches.append(
                Match(
                    url=row["url"],
                    team_a_name=row["team_a_name"],
                    team_a_odds=float(row["team_a_odds"]),
                    team_b_name=row["team_b_name"],
                    team_b_odds=float(row["team_b_odds"]),
                    recorded_date=row["recorded_date"],
                    pred=Prediction(row["pred"]),
                    winner=Team(row["winner"]),
                    date=row["date"],
                )
            )

    return matches


def write_event_csv(match_id: str, matches: list[Match]):
    with open(f"{match_id}.csv", "w", newline="") as csvfile:
        fieldnames = list(Match.__annotations__)
        writer = csv.DictWriter(csvfile, dialect="excel-tab", fieldnames=fieldnames)

        writer.writeheader()
        for odds in matches:
            writer.writerow(asdict(odds))


def scrape_event(event_id: str) -> list[Match]:
    existing_matches = read_match_csv(event_id)
    matches_to_write: list[Match] = []
    existing_urls = [match.url for match in existing_matches]

    match_urls = get_matches(event_id)

    for url in match_urls:
        if url in existing_urls:
            existing_match = next(x for x in existing_matches if x.url == url)

            if (
                datetime.strptime(existing_match.date, "%Y-%m-%d %H:%M:%S").replace(
                    tzinfo=UTC
                )
                + timedelta(days=1)
            ) < datetime.now(UTC) and existing_match.winner == Team.Unknown:
                print(
                    "Updating winner for",
                    url,
                    "as the winner is unknown and it has concluded",
                )
                existing_match.update_winner()
                existing_match.calculate_winnings()

            matches_to_write.append(existing_match)

            continue

        odds = get_odds(url)
        if odds is not None:
            matches_to_write.append(odds)

    write_event_csv(event_id, matches_to_write)

    return matches_to_write


def main() -> None:
    EMEA = "2498"
    PACIFIC = "2500"
    CHINA = "2499"
    AMERICAS = "2501"
    CHAMPS = "2283"

    collected: list[Match] = []

    # poor china
    scrape_event(CHINA)

    collected.extend(scrape_event(PACIFIC))
    collected.extend(scrape_event(AMERICAS))
    collected.extend(scrape_event(EMEA))
    collected.extend(scrape_event(CHAMPS))

    def filter_match(match: Match) -> bool:
        if match.pred == Prediction.Unknown or match.pred == Prediction.Split:
            return False

        if match.winner == Team.Unknown:
            return False

        return True

    write_event_csv("collected", list(filter(filter_match, collected)))


if __name__ == "__main__":
    main()
