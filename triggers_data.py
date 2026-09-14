"""
"Triggers tidslinjen" - en handplockad, rankad lista med potentiella
framtida händelser som skulle kunna påverka ett bolags aktiekurs kraftigt
(produktlanseringar, myndighetsbeslut, kliniska studiedata, stämningar,
kapacitetsbeslut m.m.).

VIKTIGT: det finns ingen fri, strukturerad "trigger-kalender"-API för
börsbolag (till skillnad från rapportdatum/utdelningar, se scoring.py:s
_upcoming_events som hämtas live från Yahoo Finance). Listan här är
istället en bedömning gjord av Claude (AI) utifrån allmän kunskap om
bolagen - INTE verifierad realtidsdata. Datum är uppskattningar och kan
redan ha passerat eller ändrats. TRIGGERS_DISCLAIMER nedan skickas alltid
med till frontend och visas synligt ovanför tidslinjen av just den
anledningen.

Rankad 1 (störst bedömd potentiell kurspåverkan) till 50 (minst, men
fortfarande betydande). Uppdateras inte automatiskt - en framtida
förbättring skulle kunna knyta an till en riktig nyhets-/händelsedata-
källa, men ingen sådan är tillgänglig gratis idag.
"""

from datetime import datetime, timezone

TRIGGERS_DISCLAIMER = (
    "Den här listan är en bedömning gjord av AI utifrån allmän kunskap om "
    "bolagen - inte verifierad realtidsdata från en nyhetskälla. Datum är "
    "uppskattningar och kan redan ha passerat, flyttats eller ändrats. Se "
    "det som en översikt att undersöka vidare, inte en garanti."
)


def _ts(date_str: str) -> float:
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()


_RAW_TRIGGERS = [
    (1, "Nvidia", "NVDA", "2026-11-19", "Kvartalsrapport och uppdatering om nästa generations AI-chip (Rubin) - marknadens viktigaste mått på om AI-datacenterinvesteringarna fortsätter i samma takt."),
    (2, "Alphabet (Google)", "GOOGL", "2026-10-01", "Väntad dom/åtgärdsbeslut i den amerikanska antitrust-processen om Googles sökmonopol, som kan tvinga fram strukturella förändringar i affärsmodellen."),
    (3, "Apple", "AAPL", "2027-03-15", "Väntat vårevent med uppdaterade iPad/Mac-modeller och nästa steg i den AI-drivna Siri-satsningen, som marknaden bevakar efter tidigare förseningar."),
    (4, "Tesla", "TSLA", "2026-10-21", "Kvartalsrapport med uppdatering om Cybercab-produktionsstart och Robotaxi-utrullningens takt, båda avgörande för värderingen bortom bilförsäljningen."),
    (5, "Eli Lilly", "LLY", "2026-12-01", "Väntade fas 3-data för nästa generations fetma-/diabetesläkemedel (orforglipron i tablettform) som kan omdefiniera konkurrensen mot Novo Nordisk."),
    (6, "Novo Nordisk", "NVO", "2027-01-15", "Väntade långtidsdata för CagriSema och uppdaterad konkurrensbild mot Eli Lilly inom fetmaläkemedel - avgörande för bolagets ledande marknadsposition."),
    (7, "Microsoft", "MSFT", "2026-11-17", "Ignite-konferensen med uppdatering om Copilot/Azure AI-intäkter och det fortsatta samarbetet med OpenAI, en nyckelfråga för aktien."),
    (8, "Boeing", "BA", "2026-12-10", "Väntad certifiering av 777X-modellen efter upprepade förseningar - avgörande för att återställa förtroendet och kassaflödet."),
    (9, "TSMC", "TSM", "2027-01-16", "Kvartalsrapport med utsikter för 2nm-produktion och kapacitetsutbyggnad - central indikator för hela halvledarkedjan."),
    (10, "Amazon", "AMZN", "2026-12-01", "AWS re:Invent-konferensen med nya AI-tjänster (Trainium-chip, Bedrock) som ska visa att AWS håller jämna steg med Microsoft/Google i AI-racet."),
    (11, "Meta Platforms", "META", "2027-01-28", "Kvartalsrapport där marknaden särskilt bevakar avkastningen på de enorma AI-datacenterinvesteringarna och Reality Labs-förlusterna."),
    (12, "ASML", "ASML", "2027-01-21", "Kvartalsrapport med orderingång för EUV-litografimaskiner - en tidig indikator på hela chipindustrins investeringsvilja, extra känslig för Kina-exportregler."),
    (13, "Volvo Cars", "VOLCAR-B.ST", "2026-10-22", "Kvartalsrapport som visar hur snabbt lönsamheten i den rena elbilsportföljen (EX30/EX90) förbättras efter tidigare nedskrivningar."),
    (14, "Ericsson", "ERIC-B.ST", "2026-10-16", "Kvartalsrapport med uppdatering om 5G-kontraktsläget i Nordamerika och marginalutvecklingen efter flera års kostnadsbesparingar."),
    (15, "AMD", "AMD", "2027-02-04", "Kvartalsrapport och uppdatering om MI400-AI-acceleratorernas kundorder - avgörande för om AMD kan ta marknadsandelar från Nvidia."),
    (16, "Pfizer", "PFE", "2026-12-15", "Väntat FDA-besked om ett nyare cancer- eller fetmaläkemedel i sen fas, viktigt för att fylla intäktstappet efter covid-produkternas nedgång."),
    (17, "Coinbase", "COIN", "2026-11-05", "Regleringsbesked (SEC/CFTC) om kryptoderivat och stablecoin-regler i USA som direkt påverkar Coinbases intäktsmix."),
    (18, "Berkshire Hathaway", "BRK-B", "2027-02-28", "Årsredovisning och Warren Buffetts aktieägarbrev - extra bevakat givet successionen till Greg Abel och den historiskt stora kassahögen."),
    (19, "Disney", "DIS", "2026-11-12", "Kvartalsrapport med uppdatering om Disney+ lönsamhet och hur parkbesök/streaming utvecklas i en svagare konsumentmiljö."),
    (20, "Intel", "INTC", "2027-01-22", "Kvartalsrapport med uppdatering om 18A-tillverkningsprocessen och foundry-kundernas intresse - avgörande för turnaround-planen."),
    (21, "JPMorgan Chase", "JPM", "2027-01-14", "Kvartalsrapport som brukar sätta tonen för hela bankrapportsäsongen, med särskilt fokus på kreditförluster och räntenettots utveckling."),
    (22, "Novartis", "NVS", "2026-10-29", "Kvartalsrapport med uppdatering om lanseringen av flera nya cancer- och njurläkemedel efter avknoppningen av Sandoz."),
    (23, "H&M", "HM-B.ST", "2026-12-11", "Kvartalsrapport (fjärde kvartalet) som visar om lagerhanteringen och prissättningen förbättrat marginalen inför vårkollektionen."),
    (24, "Evolution AB", "EVO.ST", "2026-10-28", "Kvartalsrapport med uppdatering om regulatoriska utmaningar i vissa amerikanska delstater och tillväxten i Asien - en återkommande kursrisk."),
    (25, "Broadcom", "AVGO", "2026-12-11", "Kvartalsrapport med uppdatering om anpassade AI-chip (ASIC) till stora molnbolag - ett skifte som konkurrerar med Nvidias standardchip."),
    (26, "BYD", "1211.HK", "2026-11-25", "Uppdatering om exportvolymer till Europa och Sydostasien, som avgör om BYD kan fortsätta ta marknadsandelar globalt trots handelstullar."),
    (27, "Visa", "V", "2027-01-27", "Kvartalsrapport med uppdatering om gränsöverskridande transaktionsvolymer - en känslig indikator på global konsumtion och resande."),
    (28, "Netflix", "NFLX", "2027-01-20", "Kvartalsrapport med uppdatering om annonsfinansierade abonnemang och livesport-satsningens lönsamhet."),
    (29, "Spotify", "SPOT", "2026-10-29", "Kvartalsrapport som visar om prishöjningarna 2026 slagit igenom i marginalen utan att tappa för många abonnenter."),
    (30, "Rivian", "RIVN", "2027-02-25", "Uppdatering om produktionsrampen för den billigare R2-modellen, avgörande för om Rivian kan nå positivt kassaflöde."),
    (31, "Roche", "ROG.SW", "2026-12-08", "Väntade studiedata för nästa generations Alzheimer- och fetmaläkemedel i den sena utvecklingsportföljen."),
    (32, "Sandvik", "SAND.ST", "2026-10-23", "Kvartalsrapport med orderingång inom gruv- och verktygsutrustning - en tidig konjunktursignal för global industriproduktion."),
    (33, "Atlas Copco", "ATCO-A.ST", "2026-10-27", "Kvartalsrapport med orderingång inom kompressorer och vakuumteknik, extra känslig för halvledarindustrins investeringstakt."),
    (34, "Alibaba", "9988.HK", "2026-11-19", "Kvartalsrapport med uppdatering om molntjänsternas AI-drivna tillväxt och konkurrensen från statligt stödda kinesiska AI-bolag."),
    (35, "Boliden", "BOL.ST", "2026-10-22", "Kvartalsrapport extra känslig för koppar- och zinkpriser, som stigit kraftigt på förväntningar om elektrifiering och AI-datacentrens elbehov."),
    (36, "Airbus", "AIR.PA", "2027-02-18", "Årsrapport med uppdatering om leveranstakten för A320neo-familjen efter återkommande problem i motorleverantörskedjan."),
    (37, "Sinch", "SINCH.ST", "2026-10-21", "Kvartalsrapport som visar om skuldsaneringen och lönsamhetsvändningen fortsätter enligt plan efter flera tuffa år."),
    (38, "Moderna", "MRNA", "2026-11-06", "Kvartalsrapport med uppdatering om pipeline bortom covidvacciner (cancervaccin, RSV) som ska kompensera för fallande vaccinintäkter."),
    (39, "Shell", "SHEL", "2026-10-29", "Kvartalsrapport med uppdatering om LNG-strategin och kapitalallokering mellan förnybart och olja/gas efter det uppköpta LNG-bolaget."),
    (40, "Hexagon", "HEXA-B.ST", "2026-10-15", "Kvartalsrapport med uppdatering om efterfrågan på mätteknik/digitala tvillingar inom tillverkningsindustrin."),
    (41, "Nibe Industrier", "NIBE-B.ST", "2026-10-23", "Kvartalsrapport som visar om värmepumpsmarknaden i Europa återhämtat sig efter två svaga år med lågt byggande."),
    (42, "SEB", "SEB-A.ST", "2027-01-28", "Kvartalsrapport med uppdatering om kreditförluster inom fastighetssektorn, en fortsatt riskfaktor för svenska storbanker."),
    (43, "Investor AB", "INVE-B.ST", "2026-11-13", "Kvartalsrapport där substansvärderabatten och utvecklingen i de största innehaven (Atlas Copco, Ericsson, AstraZeneca) är i fokus."),
    (44, "Essity", "ESSITY-B.ST", "2026-10-21", "Kvartalsrapport som visar hur väl prishöjningar kompenserat för fortsatt höga massa- och energikostnader."),
    (45, "T-Mobile US", "TMUS", "2026-10-23", "Kvartalsrapport med uppdatering om abonnenttillväxt inom hemmabredband via 5G, en snabbt växande intäktskälla."),
    (46, "Telia Company", "TELIA.ST", "2026-10-20", "Kvartalsrapport med uppdatering om avyttringar utanför Norden och skuldsättningens utveckling."),
    (47, "Electrolux", "ELUX-B.ST", "2026-10-30", "Kvartalsrapport som visar om omstruktureringsprogrammet i Nordamerika äntligen börjar ge lönsamhetseffekt."),
    (48, "SKF", "SKF-B.ST", "2026-10-24", "Kvartalsrapport med orderingång inom industrilager - ytterligare en tidig konjunktursignal för europeisk industriproduktion."),
    (49, "Alfa Laval", "ALFA.ST", "2026-10-29", "Kvartalsrapport med orderingång inom energiomställning och marina lösningar, ett område med stark strukturell tillväxt."),
    (50, "Handelsbanken", "SHB-A.ST", "2027-01-29", "Kvartalsrapport med uppdatering om räntenetto och kreditkvalitet i den svenska bolånestocken."),
]

TRIGGERS = [
    {
        "rank": rank,
        "company": company,
        "ticker": ticker,
        "date": _ts(date_str),
        "description": description,
    }
    for rank, company, ticker, date_str, description in _RAW_TRIGGERS
]
