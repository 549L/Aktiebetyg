# Aktiebetyg

En liten lokal webbapp som betygsätter ett börsbolag 1-100 baserat på
nyckeltal, och ger 3 positiva och 3 negativa punkter om bolaget. Skalan är
inriktad på "kvalitetstillväxt till rimligt pris" - bolag som växer
lönsamt, är finansiellt sunda, och inte är orimligt dyra i förhållande till
sin tillväxt.

## Komma igång

```bash
pip install -r requirements.txt
python app.py
```

Öppna sedan http://localhost:5000 i webbläsaren och skriv in ett
bolagsnamn (t.ex. "Volvo", "Ericsson") eller en exakt ticker (t.ex. `AAPL`,
`VOLV-B.ST`). Sökningen visar bara bolagets egen hemmabörs, inte utländska
cross-listings/depåbevis.

## Betygskurvan per nyckeltal

Varje nyckeltals delbetyg (0-100) räknas ut med en mjuk, klockformad
(gaussisk) avklingningskurva kring idealvärdet - inte ett rakt streck till
en hård gräns. Ett värde precis vid den gamla "gränsen" (`scale`/`floor`/
`ceiling` i `config/metrics.py`) ger fortfarande ~13 poäng istället för
exakt 0, så gränsfall bedöms mer graderat. Se `_gaussian_falloff` i
[`scoring.py`](scoring.py).

Kurvan är kalibrerad så att 90+ ska vara ovanligt och betyda "genuint
enastående bolag", inte bara "bra bolag". Två saker styr det: `_SIGMA_DIVISOR`
i `scoring.py` (brantare avklingning - kräver att man ligger riktigt nära
idealvärdet, inte bara "hyfsat nära", för att hålla sig kvar nära 100 på ett
nyckeltal) och att flera `ideal`-värden i `config/metrics.py` höjts till en
mer krävande nivå (t.ex. Rule of 40 40→55, SaaS-tillväxt 25%→30%,
bruttomarginal 70%→75%). Ett bolag som Microsoft gick från 92 till 81 med
den nya kalibreringen - fortfarande bra, men inte längre "topp-betyg" bara
för att vara stort och lönsamt. Ett fåtal verkligt dominanta bolag (t.ex.
TSMC, Investor AB) ligger fortfarande kvar över 90.

## Sektoranpassade betygsskalor

Olika sektorer fungerar finansiellt helt olika, så samma nyckeltal betyder
inte samma sak överallt - ett fastighetsbolag SKA ha hög skuldsättning
(det är hur sektorn fungerar), och PEG-talet blir närmast slumpmässigt för
banker. Appen väljer därför automatiskt en av flera **profiler** i
[`config/metrics.py`](config/metrics.py) beroende på bolagets Yahoo-sektor
(visas som "(Finans)" etc. ovanför nyckeltalstabellen). Matchningen sker på
sektor-nivå (Yahoos 11 huvudsektorer), inte på finare "industry"-nivå:

- **Övrigt** (kvalitetstillväxt, fallback om sektor saknas): PEG-tal,
  omsättningstillväxt, ROE, skuldsättningsgrad.
- **Industri** (Industrials): EV/EBITDA, rörelsemarginal (EBIT),
  omsättningstillväxt (orderingång-proxy), ROA
  (kapacitetsutnyttjande-proxy), fritt kassaflöde-marginal.
- **Teknik** (Technology): omsättningstillväxt, bruttomarginal, Rule of 40
  (tillväxt % + marginal %), P/S-tal, fritt kassaflöde-marginal
  (kundretention-proxy).
- **Finans** (Financial Services - banker, investmentbolag, försäkring
  m.fl.): P/B-tal (viktigast), ROE, ROA (CET1-proxy), intäktstillväxt
  (räntenetto-proxy), vinstmarginal (kreditkvalitet-proxy).
- **Råvaror** (Basic Materials) och **Energi** (Energy) - samma skala:
  EV/EBITDA, rörelsemarginal (produktionskostnad-proxy), fritt
  kassaflöde-marginal, skuldsättning (reservlivslängd-proxy).
- **Konsument cyklisk** (Consumer Cyclical) och **Konsumentstabil**
  (Consumer Defensive) - samma skala: omsättningstillväxt (jämförbar
  försäljning-proxy), bruttomarginal, rörelsemarginal, kassalikviditet
  (lageromsättning-proxy).
- **Fastigheter** (Real Estate): P/B-tal (NAV-proxy), direktavkastning,
  skuldsättning (LTV-proxy, hög tolerans), rörelsemarginal
  (förvaltningsresultat-proxy), fritt kassaflöde-marginal
  (räntetäckning-proxy).
- **Kommunikation** (Communication Services - telekom, internetbolag
  m.fl.): EV/EBITDA, nettoskuld/EBITDA, fritt kassaflöde-marginal
  (capex-proxy), direktavkastning (ARPU-proxy).
- **Hälsovård** (Healthcare - allt från förlustdrivande bioteknik till
  etablerad läkemedelsindustri): omsättningstillväxt (pipeline-proxy),
  P/S-tal (FoU-intensitet-proxy), vinstmarginal (FoU-effektivitet-proxy),
  skuldsättning (patentrisk-proxy).
- **Allmännyttigt** (Utilities): direktavkastning, skuldsättning (hög
  tolerans), P/E-tal, omsättningstillväxt.

Flera nyckeltal som brukar användas i respektive sektor (CET1, ARPU,
pipeline-värde, orderingång, lageromsättningshastighet m.fl.) rapporteras
inte i Yahoos gratis-API. Där ersätts de av närmast tillgängliga substitut
(kommenterat i `config/metrics.py` för varje profil) - några räknas ut
själv i `scoring.py` (P/S, nettoskuld/EBITDA, fritt kassaflöde-marginal,
Rule of 40, kassa-runway) eftersom Yahoo inte ger dem som färdiga fält.

Varje profil har egna **SCORING**-nyckeltal (påverkar betyget) och
**INSIGHT**-nyckeltal (bara positiva/negativa punkter). Ändra `ideal`,
`weight`, lägg till en ny profil, eller gå tillbaka till finare
branschindelning genom att lägga till `"industry:<Yahoo-bransch>"`-nycklar
i `PROFILES` (de testas före sektor-nycklarna) - allt görs i
`config/metrics.py`, som har utförliga kommentarer om varje fält och
varför idealvärdena är satta som de är.

## Data från Yahoo Finance

Appen hämtar data gratis direkt från Yahoo Finances (inofficiella) API via
[`yahoo_client.py`](yahoo_client.py), ingen API-nyckel behövs. Vissa
nyckeltal kan saknas för vissa bolag (särskilt mindre/utländska bolag) - då
räknas betyget om proportionerligt mot de nyckeltal som faktiskt finns.

Appen använder INTE `yfinance`-biblioteket, eftersom det drar in `pandas`
som beroende - och `pandas` kompilerade DLL-fil blockeras av Windows Smart
App Control på den här datorn (inte signerad på "Enterprise"-nivå).

## Fear & Greed-index (per aktie)

Varje profil innehåller ett lätt viktat (10%) nyckeltal - "Aktiens Fear &
Greed-index" - byggt från aktiens EGEN kurshistorik (RSI + position i
52-veckorsintervallet), inte ett marknadsbrett index. Lågt värde = aktien
är översåld/nära sitt årslägsta (kan vara ett köpläge enligt
kontrarian-logik), högt värde = överköpt/nära sitt årshögsta. Visas som en
egen badge i resultatkortet.

Varje profil har också ett nyckeltal för **pris vs MA200** (200 dagars
glidande medelvärde) - handlas aktien över sitt MA200 räknas det som en
långsiktig uppåttrend (grönt i tabellen), under som en nedåttrend (rött).
Både Fear & Greed och MA200 räknas ut från samma års kurshistorik i ett
och samma anrop, se [`stock_sentiment.py`](stock_sentiment.py).

## Tillväxtbolag / Stabila bolag-vy

Bredvid sökfältet finns två knappar - "Tillväxtbolag" och "Stabila bolag" -
som viktar om nyckeltalen inom vald sektorprofil, utan att byta profil.
Teknik har fortfarande sin skala och Fastigheter sin, men inom respektive
profil viktas tillväxtnyckeltal (omsättningstillväxt, Rule of 40, P/S-tal)
upp och lönsamhets-/stabilitetsnyckeltal (marginaler, skuldsättning,
utdelning, P/E, P/B m.fl.) ned i tillväxtvyn - och tvärtom i stabil-vyn.
Otaggade nyckeltal (Fear & Greed, MA200, PEG) väger lika mycket i båda
vyerna.

Taggningen sker per nyckeltals `key` i `METRIC_STYLE` i
[`config/metrics.py`](config/metrics.py), själva omviktningen (multiplicera
vikt, normalisera om så summan blir 1.0) i `_apply_view_style` i
[`scoring.py`](scoring.py). Alla 12 profiler har minst ett tillväxt- och
ett stabilitetstaggat nyckeltal i sin SCORING-lista, så knapparna ger
verklig differentiering oavsett bransch (t.ex. ett REIT som Omega
Healthcare Investors gick 76 → 81 → 74 mellan neutral/tillväxt/stabil-vy i
test). Valt läge skickas som `?style=growth|stability` till
`/api/analyze/<ticker>` och visas i resultatkortets rubrik, t.ex.
"(Fastigheter · Tillväxtvy)".

## Nyckeltalstabellen: idealvärden och färgkodning

Tabellen "Nyckeltal i betygsskalan" visar ett idealvärde per nyckeltal
(t.ex. "≥ 25,0 %" eller "≤ 8,0") så du ser exakt vad skalan strävar mot,
och färgkodar värdet/delbetyget grönt (≥70), gult (40-69) eller rött (<40)
för att göra det snabbare att läsa av.

## Kursgraf

Varje analyserad aktie visar en kursgraf med växlingsbara tidsperioder
(Dag, Vecka, 1 år, 5 år, 10 år), hämtad från Yahoos chart-API. Grafen har
riktiga axlar - Y-axel med prisnivåer, X-axel med tidpunkter anpassade
efter vald period (klockslag för Dag, datum för Vecka, månad/år för 1 år,
årtal för 5/10 år) - och gridlines för att göra den lättare att läsa av.

Ritningen i [`static/app.js`](static/app.js) (`loadChart`) bygger på
återanvändbara skalfunktioner (`xScale`/`yScale`) sparade i `currentChart`,
så att fler serier (t.ex. glidande medelvärden eller andra indikatorer)
kan ritas ovanpå med exakt samma koordinatsystem som prislinjen.

## MACD-indikator

Bredvid tidsperiod-knapparna finns en av/på-knapp för MACD (12, 26, close,
9) - standardformeln (EMA 12 minus EMA 26, med en 9-perioders EMA som
signallinje). Räknas ut helt i webbläsaren (`computeMACD` i
[`static/app.js`](static/app.js)) från samma kursdata som redan hämtats
för prisgrafen, så inget extra API-anrop behövs. Ritas i en egen panel
under prisgrafen som återanvänder samma `xScale` som prislinjen, så
tidsaxeln alltid stämmer perfekt överens mellan de två.

## Senast sökta

Under sökfältet visas en "Senast sökta"-lista över de 10 senast
analyserade aktierna, senast sökt först. Söker du på samma aktie igen
flyttas den fram till toppen igen. Historiken (inklusive tidsstämpel för
senaste sökning) sparas i [`data/history.json`](data/history.json).

## Nästa steg: TradingView-indikatorer

Tanken är att kunna mata in indikatorer/data från TradingView senare. Enklast
sätt att bygga ut detta:

1. Lägg till en ny post i `SCORING_METRICS` eller `INSIGHT_METRICS` i
   `config/metrics.py` med `"source": "manual:<namn>"`.
2. Utöka `/api/analyze/<ticker>` i `app.py` att ta emot extra värden (t.ex.
   via query-parametrar eller POST-body) och skicka dem vidare till
   `analyze_ticker` i `scoring.py`.
3. Claude kan då analysera skärmdumpar/data från TradingView och skicka in
   de färdiga värdena i det nya fältet.
