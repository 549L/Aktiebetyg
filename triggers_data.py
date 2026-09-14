"""
"Triggers tidslinjen" - en handplockad, rankad lista med potentiella
framtida händelser inom de närmaste ~2 månaderna som skulle kunna
påverka ett bolags aktiekurs kraftigt (kvartalsrapporter, myndighets-
beslut, kliniska studiedata m.m.), samt en ungefärlig bedömning av hur
mycket aktien skulle kunna röra sig procentuellt beroende på utfall.

VIKTIGT: det finns ingen fri, strukturerad "trigger-kalender"-API för
börsbolag (till skillnad från rapportdatum/utdelningar, se scoring.py:s
_upcoming_events som hämtas live från Yahoo Finance). Listan här är
istället en bedömning gjord av Claude (AI) utifrån allmän kunskap om
bolagen - INTE verifierad realtidsdata, och procentuella rörelser är
grova historiska tumregler, INTE en prognos. Datum är uppskattningar och
kan redan ha passerat eller ändrats. TRIGGERS_DISCLAIMER nedan skickas
alltid med till frontend och visas synligt ovanför tidslinjen av just
den anledningen.

Rankad 1 (störst bedömd potentiell kurspåverkan) till 20 (minst, men
fortfarande betydande). Uppdateras inte automatiskt - en framtida
förbättring skulle kunna knyta an till en riktig nyhets-/händelsedata-
källa, men ingen sådan är tillgänglig gratis idag.

/api/triggers filtrerar dessutom bort allt äldre än idag eller mer än
~2 månader (60 dagar) framåt vid varje anrop (se app.py), så listan
alltid håller sig inom det fönster användaren bad om även om den här
filen inte uppdaterats på ett tag.
"""

from datetime import datetime, timezone

TRIGGERS_DISCLAIMER = (
    "Den här listan är en bedömning gjord av AI utifrån allmän kunskap om "
    "bolagen - inte verifierad realtidsdata från en nyhetskälla. De "
    "procentuella rörelserna är grova historiska tumregler, inte en "
    "prognos. Datum är uppskattningar och kan redan ha passerat, flyttats "
    "eller ändrats. Se det som en översikt att undersöka vidare, inte en "
    "garanti."
)


def _ts(date_str: str) -> float:
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()


# (rank, bolag, ticker, datum, beskrivning, ~nedsida vid negativt utfall %, ~uppsida vid positivt utfall %)
_RAW_TRIGGERS = [
    (1, "Alphabet (Google)", "GOOGL", "2026-10-01", "Väntat åtgärdsbeslut i den amerikanska antitrust-processen om Googles sökmonopol - kan tvinga fram strukturella förändringar i affärsmodellen.", 15, 8),
    (2, "Tesla", "TSLA", "2026-10-21", "Kvartalsrapport med uppdatering om Cybercab-produktionsstart och Robotaxi-utrullningens takt, avgörande för värderingen bortom bilförsäljningen.", 15, 12),
    (3, "Eli Lilly", "LLY", "2026-10-30", "Kvartalsrapport och väntade data för nästa generations GLP-1-tablett (orforglipron), central i konkurrensen mot Novo Nordisk.", 10, 15),
    (4, "Novo Nordisk", "NVO", "2026-11-05", "Kvartalsrapport med uppdatering om CagriSema-data och konkurrensläget mot Eli Lilly inom fetmaläkemedel.", 18, 12),
    (5, "Meta Platforms", "META", "2026-10-29", "Kvartalsrapport där marknaden särskilt bevakar avkastningen på de stora AI-datacenterinvesteringarna.", 12, 9),
    (6, "Coinbase", "COIN", "2026-10-30", "Kvartalsrapport tillsammans med väntade regleringsbesked om stablecoin- och kryptoderivatregler i USA.", 15, 15),
    (7, "ASML", "ASML", "2026-10-15", "Kvartalsrapport med orderingång för EUV-litografimaskiner - en tidig indikator för hela chipindustrins investeringsvilja.", 12, 10),
    (8, "Intel", "INTC", "2026-10-23", "Kvartalsrapport med uppdatering om 18A-tillverkningsprocessen och foundry-kundernas intresse - avgörande för turnaround-planen.", 12, 10),
    (9, "Boeing", "BA", "2026-10-28", "Kvartalsrapport med uppdatering om 777X-certifieringen efter upprepade förseningar - avgörande för kassaflödet.", 10, 8),
    (10, "Amazon", "AMZN", "2026-10-30", "Kvartalsrapport med fokus på AWS-tillväxten och hur väl den håller jämna steg med Microsoft/Google i AI-racet.", 8, 8),
    (11, "AMD", "AMD", "2026-11-04", "Kvartalsrapport och uppdatering om MI400-AI-acceleratorernas kundorder - avgörande för om AMD kan ta marknadsandelar från Nvidia.", 10, 9),
    (12, "Netflix", "NFLX", "2026-10-20", "Kvartalsrapport med uppdatering om det annonsfinansierade abonnemangets tillväxt och livesportens lönsamhet.", 10, 8),
    (13, "TSMC", "TSM", "2026-10-16", "Kvartalsrapport med utsikter för 2nm-produktion och kapacitetsutbyggnad - central indikator för hela halvledarkedjan.", 8, 6),
    (14, "Apple", "AAPL", "2026-10-30", "Kvartalsrapport med de första försäljningssiffrorna för iPhone 17-serien under en hel kvartalscykel.", 6, 6),
    (15, "Microsoft", "MSFT", "2026-10-28", "Kvartalsrapport med fokus på Azure-tillväxten och lönsamheten i Copilot/AI-satsningen tillsammans med OpenAI.", 7, 7),
    (16, "JPMorgan Chase", "JPM", "2026-10-14", "Kvartalsrapport som brukar sätta tonen för hela bankrapportsäsongen, med fokus på kreditförluster och räntenetto.", 5, 4),
    (17, "Evolution AB", "EVO.ST", "2026-10-22", "Kvartalsrapport med uppdatering om regulatoriska utmaningar i vissa amerikanska delstater - en återkommande kursrisk.", 15, 8),
    (18, "Volvo AB", "VOLV-B.ST", "2026-10-22", "Kvartalsrapport med orderingång för tunga lastbilar, en tidig konjunktursignal för europeisk industri.", 8, 6),
    (19, "Ericsson", "ERIC-B.ST", "2026-10-16", "Kvartalsrapport med uppdatering om 5G-kontraktsläget i Nordamerika och marginalutvecklingen.", 7, 6),
    (20, "H&M", "HM-B.ST", "2026-09-25", "Kvartalsrapport (tredje kvartalet) som visar om lagerhantering och prissättning förbättrat marginalen.", 6, 6),
]

TRIGGERS = [
    {
        "rank": rank,
        "company": company,
        "ticker": ticker,
        "date": _ts(date_str),
        "description": description,
        "impact_down": impact_down,
        "impact_up": impact_up,
    }
    for rank, company, ticker, date_str, description, impact_down, impact_up in _RAW_TRIGGERS
]
