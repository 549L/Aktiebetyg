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


# (rank, bolag, ticker, datum, beskrivning,
#  ~nedsida vid negativt utfall %, vad ett negativt utfall skulle innebära,
#  ~uppsida vid positivt utfall %, vad ett positivt utfall skulle innebära)
_RAW_TRIGGERS = [
    (1, "Alphabet (Google)", "GOOGL", "2026-10-01", "Väntat åtgärdsbeslut i den amerikanska antitrust-processen om Googles sökmonopol.",
     15, "Ett beslut om att tvinga fram en uppdelning av bolaget skulle slå hårt mot värderingen.",
     8, "Ett milt beslut utan tvångsavyttring skulle lätta ett stort orosmoln."),
    (2, "Tesla", "TSLA", "2026-10-21", "Kvartalsrapport med uppdatering om Cybercab-produktionsstart och Robotaxi-utrullningens takt.",
     15, "Ytterligare förseningar eller svag bilmarginal skulle väcka tvivel om värderingen.",
     12, "Tydliga tecken på att Cybercab/Robotaxi ligger i tid skulle stärka tillväxtberättelsen."),
    (3, "Eli Lilly", "LLY", "2026-10-30", "Kvartalsrapport och väntade data för nästa generations GLP-1-tablett (orforglipron).",
     10, "Svagare data eller biverkningsproblem skulle gynna konkurrenterna istället.",
     15, "Starka tablettdata skulle befästa ledarskapet inom GLP-1 före Novo Nordisk."),
    (4, "Novo Nordisk", "NVO", "2026-11-05", "Kvartalsrapport med uppdatering om CagriSema-data och konkurrensläget mot Eli Lilly.",
     18, "Ytterligare svaga data skulle befästa oron för att Eli Lilly tar över ledartröjan.",
     12, "Starka CagriSema-data skulle återupprätta förtroendet efter tidigare besvikelser."),
    (5, "Meta Platforms", "META", "2026-10-29", "Kvartalsrapport där marknaden särskilt bevakar avkastningen på AI-datacenterinvesteringarna.",
     12, "Fortsatt höga kostnader utan tydlig avkastning skulle öka oron för överinvestering.",
     9, "Tecken på att AI-investeringarna börjar ge mätbar intäktsavkastning skulle lugna marknaden."),
    (6, "Coinbase", "COIN", "2026-10-30", "Kvartalsrapport tillsammans med väntade regleringsbesked om stablecoin- och kryptoderivatregler i USA.",
     15, "Strängare regler eller oväntade avgifter skulle pressa en redan konkurrensutsatt marknad.",
     15, "Tydliga, gynnsamma regler för stablecoins skulle öppna för kraftig intäktstillväxt."),
    (7, "ASML", "ASML", "2026-10-15", "Kvartalsrapport med orderingång för EUV-litografimaskiner.",
     12, "Svag orderingång eller nya exportrestriktioner mot Kina skulle oroa hela sektorn.",
     10, "Stark orderingång skulle signalera fortsatt hög investeringsvilja i chipindustrin."),
    (8, "Intel", "INTC", "2026-10-23", "Kvartalsrapport med uppdatering om 18A-tillverkningsprocessen och foundry-kundernas intresse.",
     12, "Fortsatt svagt kundintresse skulle förstärka tvivlen på foundry-satsningens framtid.",
     10, "Tydliga tecken på att 18A vinner stora externa kunder skulle stärka turnaround-berättelsen."),
    (9, "Boeing", "BA", "2026-10-28", "Kvartalsrapport med uppdatering om 777X-certifieringen efter upprepade förseningar.",
     10, "Ytterligare en försening skulle förlänga den redan långa perioden av svagt kassaflöde.",
     8, "En godkänd certifiering skulle äntligen frigöra uppskjutna leveranser och kassaflöde."),
    (10, "Amazon", "AMZN", "2026-10-30", "Kvartalsrapport med fokus på AWS-tillväxten i AI-racet mot Microsoft/Google.",
     8, "Avmattande AWS-tillväxt skulle väcka oro för tappade marknadsandelar.",
     8, "Fortsatt stark AWS-tillväxt skulle visa att molnaffären håller jämna steg."),
    (11, "AMD", "AMD", "2026-11-04", "Kvartalsrapport och uppdatering om MI400-AI-acceleratorernas kundorder.",
     10, "Svaga eller uteblivna stororder skulle väcka tvivel om AMD:s AI-satsning.",
     9, "Stora bekräftade order skulle stärka bilden av AMD som ett verkligt AI-alternativ till Nvidia."),
    (12, "Netflix", "NFLX", "2026-10-20", "Kvartalsrapport med uppdatering om den annonsfinansierade nivåns tillväxt och livesportens lönsamhet.",
     10, "Avmattande abonnenttillväxt skulle väcka oro för mättnad på en mogen marknad.",
     8, "Stark tillväxt i annonsnivån skulle visa att den nya intäktskällan skalar väl."),
    (13, "TSMC", "TSM", "2026-10-16", "Kvartalsrapport med utsikter för 2nm-produktion och kapacitetsutbyggnad.",
     8, "Svagare utsikter skulle vara ett varningstecken för hela halvledarkedjan.",
     6, "Stark efterfrågan på 2nm-kapacitet skulle bekräfta fortsatt AI-driven chipboom."),
    (14, "Apple", "AAPL", "2026-10-30", "Kvartalsrapport med de första försäljningssiffrorna för iPhone 17-serien under en hel kvartalscykel.",
     6, "Svagare försäljning skulle förstärka bilden av Apple utan tydlig ny tillväxtmotor.",
     6, "Starkare än väntad försäljning skulle lugna oron för en mognande produktcykel."),
    (15, "Microsoft", "MSFT", "2026-10-28", "Kvartalsrapport med fokus på Azure-tillväxten och lönsamheten i AI-satsningen med OpenAI.",
     7, "Avmattande molntillväxt skulle väcka oro för att AI-hypen inte omsätts i intäkter.",
     7, "Fortsatt stark Azure-tillväxt skulle visa att AI-satsningen betalar sig."),
    (16, "JPMorgan Chase", "JPM", "2026-10-14", "Kvartalsrapport som brukar sätta tonen för hela bankrapportsäsongen.",
     5, "Stigande kreditförluster skulle väcka oro för att hushållens ekonomi försämras.",
     4, "Låga kreditförluster och starkt räntenetto skulle sätta en positiv ton för sektorn."),
    (17, "Evolution AB", "EVO.ST", "2026-10-22", "Kvartalsrapport med uppdatering om regulatoriska utmaningar i vissa amerikanska delstater.",
     15, "Ytterligare delstater som stramar åt skulle hota en betydande del av tillväxten.",
     8, "Ett gynnsamt regulatoriskt besked skulle undanröja en av bolagets största kursrisker."),
    (18, "Volvo AB", "VOLV-B.ST", "2026-10-22", "Kvartalsrapport med orderingång för tunga lastbilar, en tidig konjunktursignal.",
     8, "Svag orderingång skulle bekräfta en fortsatt svag industrikonjunktur.",
     6, "Stark orderingång skulle signalera att den europeiska lastbilscykeln vänt uppåt."),
    (19, "Ericsson", "ERIC-B.ST", "2026-10-16", "Kvartalsrapport med uppdatering om 5G-kontraktsläget i Nordamerika och marginalutvecklingen.",
     7, "Nya kontraktsförluster eller prispress skulle väcka oro för konkurrenskraften.",
     6, "Förbättrade marginaler och stabila 5G-kontrakt skulle stärka bilden av lyckad omstrukturering."),
    (20, "H&M", "HM-B.ST", "2026-09-25", "Kvartalsrapport (tredje kvartalet) som visar om lagerhantering och prissättning förbättrat marginalen.",
     6, "Fortsatt svag marginal skulle förstärka bilden av ett bolag som halkar efter konkurrenterna.",
     6, "Förbättrad marginal skulle visa att lagerhantering och prissättning äntligen fungerar."),
]

TRIGGERS = [
    {
        "rank": rank,
        "company": company,
        "ticker": ticker,
        "date": _ts(date_str),
        "description": description,
        "impact_down": impact_down,
        "outcome_down": outcome_down,
        "impact_up": impact_up,
        "outcome_up": outcome_up,
    }
    for rank, company, ticker, date_str, description, impact_down, outcome_down, impact_up, outcome_up in _RAW_TRIGGERS
]
