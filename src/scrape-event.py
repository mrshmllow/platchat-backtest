# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "beautifulsoup4"
# ]
# ///

from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import csv
from dataclasses import dataclass
from datetime import datetime
import os.path


@dataclass
class Match:
    url: str

    team_a_name: str
    team_a_odds: float

    team_b_name: str
    team_b_odds: float

    recorded_date: str


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

    if len(soup.select("div.mod-pending")) != 0 or len(match_bet) != 2:
        print("skipping", match_url, "no odds found or match concluded")
        return None

    team_a_name, team_b_name = [
        team.string for team in match_bet[0].select("span.match-bet-item-team")
    ]
    team_a_odds, team_b_odds = [
        team.string for team in match_bet[0].select("span.match-bet-item-odds")
    ]

    return Match(
        match_url,
        str(team_a_name),
        float(str(team_a_odds)),
        str(team_b_name),
        float(str(team_b_odds)),
        now.strftime("%m/%d/%Y, %H:%M:%S"),
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
                Match(row[0], row[1], float(row[2]), row[3], float(row[4]), row[5])
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
        if odds is not None:
            matches.append(odds)

    write_match_csv(event_id, matches)


def main() -> None:
    EMEA = "2498"
    PACIFIC = "2500"
    CHINA = "2499"
    AMERICAS = "2501"

    # scrape_event(CHINA)
    scrape_event(PACIFIC)
    scrape_event(AMERICAS)
    scrape_event(EMEA)


if __name__ == "__main__":
    main()
