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
fortfarande betydande). Den här filen i sig uppdateras inte automatiskt,
men triggers_store.py håller den LIVE listan vid 20 triggers: när en
plats' datum har passerat ersätts den (nästa gång /api/triggers anropas,
alltså inom minuter - gott om marginal mot "inom 1 dag") med nästa bolag
ur RESERVE_TRIGGERS nedan, med ett nytt datum längre fram. TRIGGERS här
är bara STARTuppsättningen som triggers_store.py utgår från första
gången den körs.

/api/triggers filtrerar dessutom bort allt äldre än idag eller mer än
~2 månader (60 dagar) framåt vid varje anrop (se app.py), så listan
alltid håller sig inom det fönster användaren bad om.
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


# Reservbolag - dras på av triggers_store.py för att fylla en plats vars
# händelse har passerat, så tidslinjen alltid håller 20 triggers även om
# den här filen inte uppdaterats på länge (se triggers_store.py för hur
# datum/rank tilldelas dynamiskt vid påfyllning). Ingen av dessa förekommer
# redan i _RAW_TRIGGERS ovan.
# (bolag, ticker, beskrivning, ~nedsida, negativt utfall, ~uppsida, positivt utfall)
RESERVE_TRIGGERS = [
    ("Nvidia", "NVDA", "Kvartalsrapport med orderläget för nästa generations AI-acceleratorer.",
     15, "Tecken på avmattande AI-datacenterefterfrågan skulle slå hårt mot hela sektorns värdering.",
     10, "Fortsatt stark orderingång skulle bekräfta att AI-investeringscykeln inte mattas av."),
    ("Visa", "V", "Kvartalsrapport med uppdatering om den globala korttransaktionsvolymen.",
     6, "Svagare konsumtion skulle väcka oro för en bredare avmattning i hushållens spending.",
     5, "Fortsatt stabil transaktionstillväxt skulle visa att konsumenten står stark."),
    ("Walmart", "WMT", "Kvartalsrapport som brukar spegla hur den prispressade konsumenten mår.",
     6, "Svagare marginal eller försiktig prognos skulle oroa för en pressad låginkomstkonsument.",
     5, "Stark försäljningstillväxt skulle visa att bolaget tar marknadsandelar i en tuff miljö."),
    ("Nike", "NKE", "Kvartalsrapport med uppdatering om lagernivåer och återhämtningen i Kina.",
     8, "Fortsatt svag efterfrågan i Kina skulle förlänga en redan långdragen turnaround.",
     7, "Tecken på återhämtning i Kina och lägre rabatter skulle stärka marginalberättelsen."),
    ("Salesforce", "CRM", "Kvartalsrapport med fokus på hur AI-agenten Agentforce omsätts i faktiska intäkter.",
     10, "Svag Agentforce-adoption skulle väcka tvivel om bolagets AI-strategi.",
     8, "Tydlig intäktstillväxt kopplad till Agentforce skulle bekräfta AI-satsningens värde."),
    ("Pfizer", "PFE", "Kvartalsrapport med uppdatering om pipeline-projekt efter patentutgångarna på flera storsäljare.",
     8, "Ytterligare besvikelser i pipelinen skulle förstärka oron för intäktstappet efter patentklippor.",
     7, "Positiva pipeline-besked skulle visa att bolaget kan ersätta de förlorade intäkterna."),
    ("Uber", "UBER", "Kvartalsrapport med uppdatering om lönsamheten i kärnaffären och självkörande-samarbetena.",
     9, "Svagare marginal eller trögare tillväxt inom Mobility skulle oroa marknaden.",
     7, "Stark tillväxt och nya självkörande-partnerskap skulle stärka den långsiktiga berättelsen."),
    ("PayPal", "PYPL", "Kvartalsrapport med uppdatering om transaktionsmarginalen och konkurrensen från Apple Pay/Block.",
     9, "Fortsatt marginalpress skulle förstärka bilden av ett bolag som tappar prissättningsmakt.",
     7, "Stabiliserad marginal skulle visa att turnaround-arbetet under den nya ledningen fungerar."),
    ("Walt Disney", "DIS", "Kvartalsrapport med uppdatering om streamingslönsamheten och parkbesökarnas spending.",
     8, "Svagare parkbesök eller förnyade streamingförluster skulle oroa för två ben samtidigt.",
     6, "Fortsatt streaminglönsamhet och starka parksiffror skulle bekräfta vändningen."),
    ("Starbucks", "SBUX", "Kvartalsrapport som visar om \"Back to Starbucks\"-omstruktureringen börjar vända den fallande försäljningen.",
     8, "Ytterligare fallande jämförbar försäljning skulle förlänga tvivlen på omstruktureringen.",
     6, "Ett positivt trendbrott i jämförbar försäljning skulle vara ett viktigt bevis för att planen fungerar."),
    ("Adobe", "ADBE", "Kvartalsrapport med fokus på hur Firefly/AI-verktygen påverkar prissättning och abonnemangstillväxt.",
     9, "Tecken på att billigare AI-alternativ pressar priserna skulle oroa för bolagets marginalmodell.",
     7, "Stark AI-driven abonnemangstillväxt skulle visa att bolaget själv drar nytta av AI-skiftet."),
    ("Qualcomm", "QCOM", "Kvartalsrapport med uppdatering om licensintäkterna och diversifieringen bortom mobil-chip.",
     8, "Svagare mobilmarknad utan motvikt från nya segment skulle väcka oro för beroendet av Apple/Android.",
     6, "Stark tillväxt inom bil- och IoT-chip skulle visa att diversifieringen bortom mobilen fungerar."),
    ("Shopify", "SHOP", "Kvartalsrapport med uppdatering om handlarnas tillväxt inför högsäsongen.",
     10, "Avmattande handlarintäkter skulle väcka oro för att e-handelstillväxten mattas av brett.",
     8, "Fortsatt stark bruttovaruvärdestillväxt skulle bekräfta att bolaget tar marknadsandelar."),
    ("Spotify", "SPOT", "Kvartalsrapport med uppdatering om prishöjningarnas effekt på abonnenttillväxten och marginalen.",
     8, "Tecken på ökat abonnentbortfall efter prishöjningarna skulle oroa för prissättningsmakten.",
     6, "Fortsatt stark abonnenttillväxt trots prishöjningarna skulle bekräfta tjänstens starka ställning."),
    ("Airbnb", "ABNB", "Kvartalsrapport med uppdatering om bokningstillväxten och den nya satsningen på tjänster utöver boende.",
     8, "Avmattande bokningstillväxt skulle väcka oro för mättnad på kärnmarknaden.",
     6, "Stark tillväxt inom de nya tjänsterna skulle visa att bolaget lyckas bredda affären."),
    ("Novartis", "NVS", "Kvartalsrapport med uppdatering om pipeline-projekt inom hjärt-kärlsjukdomar och njursjukdomar.",
     7, "Besvikelser i sena kliniska studier skulle skada förtroendet för pipelinen.",
     6, "Positiva studieresultat skulle stärka bilden av en välfylld och diversifierad pipeline."),
]
