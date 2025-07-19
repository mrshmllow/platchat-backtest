# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "beautifulsoup4"
# ]
# ///

from typing import Literal
from enum import Enum
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import csv
from dataclasses import dataclass, field
from datetime import datetime
import os.path

import ssl

ssl._create_default_https_context = ssl._create_unverified_context

PLATCHAT_GUARANTEE = 500
NORMAL_PRED = 100


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

        self.winnings = 0

        def calculate_winnings(winner: Team):
            if self.winner == Team.Unknown:
                return

            odds = self.team_a_odds if winner == Team.A else self.team_b_odds

            if self.pred.is_team(winner):
                self.winnings = self.bet * odds
            else:
                self.winnings = 0

        calculate_winnings(self.winner)


def get_matches(stage_id: str) -> list[str]:
    URL = f"https://www.vlr.gg/event/matches/{stage_id}/"

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
        match_reader = csv.reader(csvfile, dialect="excel-tab")

        for row in match_reader:
            matches.append(
                Match(
                    url=row[0],
                    team_a_name=row[1],
                    team_a_odds=float(row[2]),
                    team_b_name=row[3],
                    team_b_odds=float(row[4]),
                    recorded_date=row[5],
                    pred=Prediction(row[6]),
                    winner=Team(row[7]),
                    date=row[8],
                )
            )

    return matches


def write_match_csv(match_id: str, matches: list[Match]):
    with open(f"{match_id}.csv", "w", newline="") as csvfile:
        spamwriter = csv.writer(csvfile, dialect="excel-tab")

        for odds in matches:
            spamwriter.writerow(
                [
                    odds.url,
                    odds.team_a_name,
                    odds.team_a_odds,
                    odds.team_b_name,
                    odds.team_b_odds,
                    odds.recorded_date,
                    odds.pred.value,
                    odds.winner.value,
                    odds.bet,
                    odds.winnings,
                    odds.date,
                ]
            )


def scrape_event(event_id: str):
    matches = read_match_csv(event_id)
    existing_urls = [match.url for match in matches]

    match_urls = get_matches(event_id)

    for url in match_urls:
        if url in existing_urls:
            print("skipping", url, "already recorded")
            continue

        odds = get_odds(url)
        print(odds)
        if odds is not None:
            matches.append(odds)

    write_match_csv(event_id, matches)


def main() -> None:
    EMEA = "2498"
    PACIFIC = "2500"
    CHINA = "2499"
    AMERICAS = "2501"

    scrape_event(CHINA)
    scrape_event(PACIFIC)
    scrape_event(AMERICAS)
    scrape_event(EMEA)


if __name__ == "__main__":
    main()
