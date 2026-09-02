"""
Konfiguration för aktiebetygsättningen.

Det här är den ENDA filen du behöver ändra i för att byta ut, justera eller
lägga till nyckeltal och betygsskalor.

VIKTIGT: Olika branscher fungerar finansiellt helt olika, så samma
nyckeltal betyder inte samma sak överallt. Ett fastighetsbolag SKA ha hög
skuldsättning (det är hur branschen fungerar), ett PEG-tal blir närmast
slumpmässigt för investmentbolag (deras "vinst" är portföljvärdeförändringar,
inte rörelseintäkter), och banker saknar helt Debt/Equity och
kassalikviditet i sina rapporter. Därför finns flera PROFILER nedan - en
uppsättning nyckeltal per bransch/sektor - istället för en enda global
skala.

STRUKTUR

PROFILES är en dict där nyckeln är:
  "default"                     - används om inget annat matchar
  "sector:<Yahoo-sektor>"        - t.ex. "sector:Real Estate"
  "industry:<Yahoo-bransch>"     - t.ex. "industry:Asset Management"
                                   (mer specifik än sektor, testas först)

Varje profil har:
  label   - visningsnamn för profilen (syns i appen så du ser vilken
            skala som använts)
  scoring - nyckeltal som PÅVERKAR betyget (1-100), med vikter
  insight - nyckeltal som bara genererar positiva/negativa punkter,
            utan att påverka betyget

scoring.py väljer profil i den ordningen: exakt bransch (industry) →
sektor (sector) → default. Yahoos engelska bransch/sektor-namn används som
nycklar här (samma som i config/industries.py), inte de svenska
översättningarna.

Fält per nyckeltal, se respektive profil för exempel:
  key      - internt namn, måste vara unikt inom profilen
  label    - visningsnamn (svenska)
  source   - fältnamn i Yahoos "info"-dict, eller "computed:<namn>"
  type     - "target" (idealvärde, avvikelse åt båda hållen sämre),
             "higher_better" (platå vid ideal), "lower_better" (platå vid
             ideal)
  format   - hur värdet visas (Python format-sträng)

Betygskurvan (i scoring.py) är MJUK, inte linjär: 100 poäng exakt vid
idealvärdet, sedan en klockformad (gaussisk) avklingning ju längre bort
värdet är från "scale"/"floor"/"ceiling" - inte en tvär klippa till 0.
Ett värde precis vid den gamla "gränsen" ger fortfarande ~13 poäng istället
för exakt 0, så gränsfall bedöms mer graderat och rättvist. "scale" (för
"target") och avståndet ideal→floor/ideal→ceiling (för "higher_better"/
"lower_better") styr fortfarande HUR SNABBT kurvan faller - mindre värde
= brantare/strängare skala, större värde = mer förlåtande skala.

Lägg till en ny profil genom att kopiera en befintlig och byta nyckeltal/
idealvärden - du behöver inte röra scoring.py.
"""

# Bolagets EGET Fear & Greed-index (0-100: lågt = rädsla/översåld, högt =
# girighet/överköpt), byggt från aktiens egen kurshistorik (RSI + position
# i 52-veckorsintervallet) - inte marknadsbrett. Lätt viktat i alla
# profiler (10%) som en kontrarian-timingsignal: en aktie nära sitt
# årslägsta och med lågt RSI har historiskt ofta varit ett bättre köpläge
# än en som handlas nära sitt årshögsta med högt RSI. Se
# stock_sentiment.py för själva beräkningen.
_FEAR_GREED_METRIC = {
    "key": "fear_greed",
    "label": "Aktiens Fear & Greed-index (momentum)",
    "source": "computed:fear_greed",
    "type": "lower_better",
    "ideal": 25,
    "ceiling": 100,
    "weight": 0.10,
    "format": "{:.0f}/100",
    "positive_text": "Aktiens eget Fear & Greed-index står i {value} - den är inte översåld just nu, vilket historiskt ofta varit ett bättre läge att köpa i än när en aktie är överköpt.",
    "negative_text": "Aktiens eget Fear & Greed-index står i {value} - den verkar överköpt just nu (nära sitt årshögsta/högt momentum), vilket historiskt ofta föregått en rekyl.",
}

# Pris vs MA200 (200 dagars glidande medelvärde) - ett av de mest använda
# trendfiltren i teknisk analys. Handlas aktien över sitt MA200 är den i en
# långsiktig uppåttrend (grönt), handlas den under är trenden nedåtriktad
# (rött). Lätt viktat (10%) i alla profiler, precis som Fear & Greed. Se
# stock_sentiment.py för beräkningen.
_MA200_METRIC = {
    "key": "ma200",
    "label": "Pris vs MA200 (200 dagars glidande medelvärde)",
    "source": "computed:ma200_pct",
    "type": "higher_better",
    "ideal": 0.10,
    "floor": -0.10,
    "weight": 0.10,
    "format": "{:+.1%}",
    "positive_text": "Aktien handlas {value} över sitt 200-dagars glidande medelvärde, ett tecken på en långsiktig uppåttrend.",
    "negative_text": "Aktien handlas {value} under sitt 200-dagars glidande medelvärde, ett tecken på en långsiktig nedåttrend.",
}


# ---------------------------------------------------------------------------
# DEFAULT - "kvalitetstillväxt till rimligt pris". Passar bolag där vinst
# och tillväxt är jämförbara och meningsfulla mått: tech, hälsovård,
# industri, sällanköp/dagligvaror, kommunikationstjänster, material, samt
# finansiella bolag som varken är banker eller renodlade investmentbolag.
# ---------------------------------------------------------------------------
_DEFAULT_SCORING = [
    {
        "key": "peg_ratio",
        "label": "PEG-tal (P/E justerat för vinsttillväxt)",
        "source": "pegRatio",
        "type": "target",
        "ideal": 1.0,
        "scale": 1.5,
        "weight": 0.24,
        "format": "{:.2f}",
        "positive_text": "PEG-talet på {value} tyder på att aktien är rimligt värderad i förhållande till sin vinsttillväxt (runt {ideal} räknas som balanserat).",
        "negative_text": "PEG-talet på {value} tyder på att du betalar mycket för tillväxten just nu jämfört med ett balanserat värde runt {ideal}.",
    },
    {
        "key": "revenue_growth",
        "label": "Omsättningstillväxt (YoY)",
        "source": "revenueGrowth",
        "type": "higher_better",
        "ideal": 0.20,
        "floor": -0.05,
        "weight": 0.20,
        "format": "{:.1%}",
        "positive_text": "Omsättningen växer med {value}, vilket är ett styrketecken för framtida utsikter.",
        "negative_text": "Omsättningen växer svagt eller krymper ({value}), vilket är en varningssignal för framtida tillväxt.",
    },
    {
        "key": "roe",
        "label": "Avkastning på eget kapital (ROE)",
        "source": "returnOnEquity",
        "type": "higher_better",
        "ideal": 0.24,
        "floor": 0.0,
        "weight": 0.21,
        "format": "{:.1%}",
        "positive_text": "ROE på {value} visar att bolaget är effektivt på att generera avkastning på det egna kapitalet.",
        "negative_text": "ROE på {value} är lägre än önskvärt, vilket kan tyda på svag lönsamhet.",
    },
    {
        "key": "debt_to_equity",
        "label": "Skuldsättningsgrad (Debt/Equity)",
        "source": "debtToEquity",
        "type": "lower_better",
        "ideal": 50,
        "ceiling": 300,
        "weight": 0.16,
        "format": "{:.1f}",
        "positive_text": "Skuldsättningsgraden på {value} är sund och tyder på låg finansiell risk.",
        "negative_text": "Skuldsättningsgraden på {value} är hög, vilket ökar den finansiella risken.",
    },
    dict(_FEAR_GREED_METRIC, weight=0.09),
    _MA200_METRIC,
]

_DEFAULT_INSIGHT = [
    {
        "key": "profit_margin",
        "label": "Vinstmarginal",
        "source": "profitMargins",
        "type": "higher_better",
        "good_threshold": 0.10,
        "bad_threshold": 0.0,
        "format": "{:.1%}",
        "positive_text": "Vinstmarginalen på {value} visar god lönsamhet.",
        "negative_text": "Vinstmarginalen på {value} är svag.",
    },
    {
        "key": "current_ratio",
        "label": "Kassalikviditet (Current ratio)",
        "source": "currentRatio",
        "type": "higher_better",
        "good_threshold": 1.5,
        "bad_threshold": 0.8,
        "format": "{:.2f}",
        "positive_text": "Kassalikviditeten på {value} visar god kortsiktig betalningsförmåga.",
        "negative_text": "Kassalikviditeten på {value} är låg, vilket kan tyda på likviditetsrisk.",
    },
    {
        "key": "dividend_yield",
        "label": "Direktavkastning",
        "source": "dividendYield",
        "type": "higher_better",
        "good_threshold": 0.02,
        "bad_threshold": 0.0,
        "format": "{:.1%}",
        "treat_missing_as_zero": True,
        "positive_text": "Direktavkastningen på {value} ger en fin bonus utöver kursutvecklingen.",
        "negative_text": "Ingen eller mycket låg utdelning ({value}).",
    },
    {
        "key": "target_upside",
        "label": "Analytikernas riktkurs vs pris",
        "source": "computed:target_upside",
        "type": "higher_better",
        "good_threshold": 0.10,
        "bad_threshold": -0.05,
        "format": "{:.1%}",
        "positive_text": "Analytikernas riktkurs ligger {value} över dagens pris.",
        "negative_text": "Analytikernas riktkurs ligger {value} under dagens pris.",
    },
]

# Delade byggstenar som återanvänds av flera profiler nedan, så du slipper
# skriva samma nyckeltal flera gånger.
_PRICE_TO_BOOK_NAV = {
    "key": "price_to_book",
    "label": "P/B-tal (pris mot bokfört värde)",
    "source": "priceToBook",
    "type": "target",
    # Ett bolag vars värde huvudsakligen är dess tillgångar (fastigheter,
    # aktieinnehav) bör helst handlas nära sitt bokförda värde/NAV - handlas
    # det klart under kan det vara köpvärt, klart över kan det vara dyrt.
    "ideal": 1.1,
    "scale": 1.2,
    "weight": 0.30,
    "format": "{:.2f}",
    "positive_text": "P/B-talet på {value} betyder att aktien handlas nära sitt bokförda värde (runt {ideal}), vilket är ett sunt utgångsläge.",
    "negative_text": "P/B-talet på {value} avviker en del från bokfört värde (runt {ideal} är balanserat), vilket kan tyda på över- eller undervärdering.",
}

_DIVIDEND_YIELD_SCORING_HIGH = {
    "key": "dividend_yield",
    "label": "Direktavkastning",
    "source": "dividendYield",
    "type": "higher_better",
    "ideal": 0.04,
    "floor": 0.0,
    "weight": 0.25,
    "format": "{:.1%}",
    "positive_text": "Direktavkastningen på {value} är stark för branschen och ger en fin bonus utöver kursutvecklingen.",
    "negative_text": "Direktavkastningen på {value} är låg för branschen.",
}

# EV/EBITDA - vanligaste värderingsmåttet för kapitalintensiva/cykliska
# branscher (industri, råvaror, telekom) där P/E blir missvisande p.g.a.
# skillnader i skuldsättning och avskrivningar mellan bolag.
_EV_EBITDA = {
    "key": "ev_ebitda",
    "label": "EV/EBITDA",
    "source": "enterpriseToEbitda",
    "type": "target",
    "ideal": 9,
    "scale": 7,
    "weight": 0.25,
    "format": "{:.1f}",
    "positive_text": "EV/EBITDA på {value} är en rimlig värdering för branschen (runt {ideal}).",
    "negative_text": "EV/EBITDA på {value} avviker en del från vad som är rimligt för branschen (runt {ideal}).",
}

# P/S-tal (pris/omsättning) - räknas ut själv (marketCap/omsättning) eftersom
# Yahoos eget fält för detta är opålitligt. Används för bolag där vinsten
# (P/E, PEG) är för volatil eller obefintlig för att vara ett bra mått,
# t.ex. tillväxt-SaaS och biotech i tidig fas.
_PRICE_TO_SALES = {
    "key": "price_to_sales",
    "label": "P/S-tal (pris mot omsättning)",
    "source": "computed:price_to_sales",
    "type": "lower_better",
    "ideal": 6,
    "ceiling": 30,
    "weight": 0.20,
    "format": "{:.1f}",
    "positive_text": "P/S-talet på {value} är rimligt för branschen (runt {ideal} eller lägre räknas som balanserat).",
    "negative_text": "P/S-talet på {value} är högt - du betalar mycket per omsättningskrona jämfört med ett balanserat värde runt {ideal}.",
}

# Nettoskuld/EBITDA - hur många års EBITDA det skulle ta att betala av
# nettoskulden. Central för kapitalintensiva/skuldtunga branscher som
# telekom. Räknas ut själv: (totalDebt - totalCash) / ebitda.
_NET_DEBT_TO_EBITDA = {
    "key": "net_debt_to_ebitda",
    "label": "Nettoskuld/EBITDA",
    "source": "computed:net_debt_to_ebitda",
    "type": "lower_better",
    "ideal": 2.5,
    "ceiling": 6,
    "weight": 0.25,
    "format": "{:.1f}x",
    "positive_text": "Nettoskulden på {value}x EBITDA är hanterbar för branschen.",
    "negative_text": "Nettoskulden på {value}x EBITDA är hög, vilket ökar ränte- och refinansieringsrisken.",
}

# Fritt kassaflöde-marginal (FCF/omsättning) - används som substitut för
# flera mått som inte finns i gratis-API:t (räntetäckningsgrad,
# capex/omsättning, "kassaflöde vid olika råvarupriser") eftersom de alla
# i grunden handlar om samma sak: genererar bolaget faktiskt pengar efter
# investeringar?
_FCF_MARGIN = {
    "key": "fcf_margin",
    "label": "Fritt kassaflöde-marginal",
    "source": "computed:fcf_margin",
    "type": "higher_better",
    "ideal": 0.10,
    "floor": -0.10,
    "weight": 0.15,
    "format": "{:.1%}",
    "positive_text": "Fritt kassaflöde på {value} av omsättningen visar att bolaget genererar gott om pengar efter investeringar.",
    "negative_text": "Fritt kassaflöde på {value} av omsättningen är svagt, vilket kan begränsa handlingsfriheten.",
}

# Avkastning på totala tillgångar (ROA) - substitut för mått som inte finns
# fritt tillgängliga (kärnprimärkapitalrelation för banker,
# kapacitetsutnyttjande för industribolag) - båda handlar i grunden om hur
# effektivt bolaget använder sin balansräkning/tillgångsbas.
_ROA = {
    "key": "roa",
    "label": "Avkastning på totala tillgångar (ROA)",
    "source": "returnOnAssets",
    "type": "higher_better",
    "ideal": 0.08,
    "floor": 0.0,
    "weight": 0.15,
    "format": "{:.1%}",
    "positive_text": "ROA på {value} visar att bolaget använder sin tillgångsbas effektivt.",
    "negative_text": "ROA på {value} är svagt, vilket kan tyda på ineffektiv användning av tillgångarna.",
}

_PROFIT_MARGIN_INSIGHT = _DEFAULT_INSIGHT[0]
_TARGET_UPSIDE_INSIGHT = _DEFAULT_INSIGHT[3]


# ---------------------------------------------------------------------------
# FASTIGHETSBOLAG (sector: Real Estate) - fastighetsbolag SKA ha hög
# skuldsättning, det är hur belånad fastighetsförvaltning fungerar. P/E och
# PEG är närmast meningslösa (redovisade "vinster" styrs mycket av
# värdeförändringar på fastighetsbeståndet).
#
# Efterfrågade nyckeltal → verkligt substitut:
#   NAV/EPRA NAV            → P/B-tal (pris mot bokfört värde/substansvärde)
#   Belåningsgrad (LTV)     → Skuldsättningsgrad (Debt/Equity)
#   Förvaltningsresultat    → Rörelsemarginal (operatingMargins)
#   Direktavkastning        → finns direkt
#   Räntetäckningsgrad      → Fritt kassaflöde-marginal (räntetäckning finns
#                             inte i gratis-API:t, men FCF-marginal fångar
#                             samma underliggande fråga: klarar bolaget sina
#                             räntekostnader med marginal?)
# ---------------------------------------------------------------------------
_REAL_ESTATE_SCORING = [
    dict(_PRICE_TO_BOOK_NAV, weight=0.20),
    dict(_DIVIDEND_YIELD_SCORING_HIGH, weight=0.20),
    {
        "key": "debt_to_equity",
        "label": "Skuldsättningsgrad / Belåningsgrad (LTV-proxy)",
        "source": "debtToEquity",
        "type": "lower_better",
        # Betydligt högre tolerans än standardskalan - belåning är själva
        # affärsmodellen för fastighetsbolag.
        "ideal": 100,
        "ceiling": 250,
        "weight": 0.14,
        "format": "{:.1f}",
        "positive_text": "Skuldsättningsgraden på {value} är hanterbar för ett fastighetsbolag.",
        "negative_text": "Skuldsättningsgraden på {value} är hög även för fastighetsbranschens mått, vilket ökar ränte- och refinansieringsrisken.",
    },
    {
        "key": "operating_margin",
        "label": "Rörelsemarginal (förvaltningsresultat-proxy)",
        "source": "operatingMargins",
        "type": "higher_better",
        "ideal": 0.45,
        "floor": 0.0,
        "weight": 0.11,
        "format": "{:.1%}",
        "positive_text": "Rörelsemarginalen på {value} tyder på ett starkt förvaltningsresultat.",
        "negative_text": "Rörelsemarginalen på {value} är svag för branschen.",
    },
    dict(_FCF_MARGIN, ideal=0.22, weight=0.08,
         label="Fritt kassaflöde-marginal (räntetäckning-proxy)",
         positive_text="Fritt kassaflöde på {value} av omsättningen tyder på god marginal att täcka räntekostnader.",
         negative_text="Fritt kassaflöde på {value} av omsättningen är svagt, vilket kan pressa räntetäckningen."),
    {
        "key": "revenue_growth",
        "label": "Hyresintäktstillväxt (YoY)",
        "source": "revenueGrowth",
        "type": "higher_better",
        "ideal": 0.07,
        "floor": -0.05,
        "weight": 0.10,
        "format": "{:.1%}",
        "positive_text": "Hyresintäkterna växer med {value}, ett gott tecken för fortsatt substansvärdetillväxt.",
        "negative_text": "Hyresintäkterna växer svagt eller krymper ({value}).",
    },
    dict(_FEAR_GREED_METRIC, weight=0.08),
    _MA200_METRIC,
]

_REAL_ESTATE_INSIGHT = [
    _PROFIT_MARGIN_INSIGHT,
    _TARGET_UPSIDE_INSIGHT,
]


# ---------------------------------------------------------------------------
# BANK & FINANS (industry: Banks - Diversified / Banks - Regional) - banker
# redovisar varken Debt/Equity eller kassalikviditet på ett sätt som går
# att jämföra med vanliga bolag (utlåning ÄR affärsmodellen), så de
# nyckeltalen utelämnas helt.
#
# Efterfrågade nyckeltal → verkligt substitut:
#   P/B-tal (viktigast)              → finns direkt, tyngst vikt
#   ROE                              → finns direkt
#   Kärnprimärkapitalrelation (CET1) → ROA (avkastning på tillgångar) -
#                                      CET1 rapporteras inte i gratis-API:t,
#                                      men ROA fångar samma underliggande
#                                      fråga: hur effektivt/säkert används
#                                      balansräkningen?
#   Räntenetto                       → Omsättningstillväxt (revenueGrowth) -
#                                      räntenettot är bankens huvudsakliga
#                                      intäkt, så intäktstillväxt är
#                                      närmaste tillgängliga proxy
#   Kreditförluster/kreditkvalitet   → Vinstmarginal - höga kreditförluster
#                                      syns direkt som lägre marginal
# ---------------------------------------------------------------------------
_BANK_SCORING = [
    dict(_PRICE_TO_BOOK_NAV, ideal=1.2, scale=1.0, weight=0.24),
    {
        "key": "roe",
        "label": "Avkastning på eget kapital (ROE)",
        "source": "returnOnEquity",
        "type": "higher_better",
        "ideal": 0.17,
        "floor": 0.0,
        "weight": 0.20,
        "format": "{:.1%}",
        "positive_text": "ROE på {value} är starkt för en bank och visar effektiv kapitalanvändning.",
        "negative_text": "ROE på {value} är svagt för en bank.",
    },
    dict(_ROA, ideal=0.014, weight=0.14,
         label="Avkastning på tillgångar (ROA, CET1-proxy)",
         format="{:.2%}",
         positive_text="ROA på {value} är starkt för en bank och tyder på god kapitalstyrka.",
         negative_text="ROA på {value} är svagt för en bank."),
    {
        "key": "revenue_growth",
        "label": "Intäktstillväxt (räntenetto-proxy)",
        "source": "revenueGrowth",
        "type": "higher_better",
        "ideal": 0.10,
        "floor": -0.05,
        "weight": 0.14,
        "format": "{:.1%}",
        "positive_text": "Intäkterna växer med {value}, ett styrketecken för räntenettot.",
        "negative_text": "Intäkterna växer svagt eller krymper ({value}).",
    },
    {
        "key": "profit_margin",
        "label": "Vinstmarginal (kreditkvalitet-proxy)",
        "source": "profitMargins",
        "type": "higher_better",
        "ideal": 0.28,
        "floor": 0.0,
        "weight": 0.09,
        "format": "{:.1%}",
        "positive_text": "Vinstmarginalen på {value} tyder på god kreditkvalitet och kontrollerade kreditförluster.",
        "negative_text": "Vinstmarginalen på {value} är svag, vilket kan tyda på högre kreditförluster.",
    },
    dict(_FEAR_GREED_METRIC, weight=0.09),
    _MA200_METRIC,
]

_BANK_INSIGHT = [
    _TARGET_UPSIDE_INSIGHT,
    {
        "key": "dividend_yield",
        "label": "Direktavkastning",
        "source": "dividendYield",
        "type": "higher_better",
        "good_threshold": 0.03,
        "bad_threshold": 0.0,
        "format": "{:.1%}",
        "treat_missing_as_zero": True,
        "positive_text": "Direktavkastningen på {value} ger en fin bonus utöver kursutvecklingen.",
        "negative_text": "Ingen eller mycket låg utdelning ({value}).",
    },
    {
        "key": "pe_ratio",
        "label": "P/E-tal",
        "source": "trailingPE",
        "fallback_source": "forwardPE",
        "type": "higher_better",
        "good_threshold": 9,
        "bad_threshold": 16,
        "format": "{:.1f}",
        "positive_text": "P/E-talet på {value} är lågt för en bank, vilket kan tyda på en attraktiv värdering.",
        "negative_text": "P/E-talet på {value} är högt för en bank jämfört med branschnormen.",
    },
]


# ---------------------------------------------------------------------------
# KRAFTFÖRSÖRJNING (sector: Utilities) - reglerade, stabila
# utdelningsbolag med hög men förutsägbar belåning. Direktavkastning väger
# tyngst, tillväxtkraven är låga.
# ---------------------------------------------------------------------------
_UTILITIES_SCORING = [
    dict(_DIVIDEND_YIELD_SCORING_HIGH, weight=0.24),
    {
        "key": "debt_to_equity",
        "label": "Skuldsättningsgrad (Debt/Equity)",
        "source": "debtToEquity",
        "type": "lower_better",
        "ideal": 120,
        "ceiling": 250,
        "weight": 0.20,
        "format": "{:.1f}",
        "positive_text": "Skuldsättningsgraden på {value} är hanterbar för ett kraftbolag.",
        "negative_text": "Skuldsättningsgraden på {value} är hög även för branschens mått.",
    },
    {
        "key": "pe_ratio",
        "label": "P/E-tal",
        "source": "trailingPE",
        "fallback_source": "forwardPE",
        "type": "target",
        "ideal": 16,
        "scale": 10,
        "weight": 0.21,
        "format": "{:.1f}",
        "positive_text": "P/E-talet på {value} ligger nära ett normalt värde för branschen (runt {ideal}).",
        "negative_text": "P/E-talet på {value} avviker från vad som är normalt för branschen (runt {ideal}).",
    },
    {
        "key": "revenue_growth",
        "label": "Omsättningstillväxt (YoY)",
        "source": "revenueGrowth",
        "type": "higher_better",
        "ideal": 0.04,
        "floor": -0.05,
        "weight": 0.16,
        "format": "{:.1%}",
        "positive_text": "Omsättningen växer med {value}, stabilt för en reglerad verksamhet.",
        "negative_text": "Omsättningen krymper ({value}), ovanligt för en reglerad verksamhet.",
    },
    dict(_FEAR_GREED_METRIC, weight=0.09),
    _MA200_METRIC,
]

_UTILITIES_INSIGHT = [_PROFIT_MARGIN_INSIGHT, _DEFAULT_INSIGHT[1], _TARGET_UPSIDE_INSIGHT]


# ---------------------------------------------------------------------------
# RÅVAROR & ENERGI (sector: Energy - olja/gas, och sector: Basic Materials -
# gruvor/metaller) - vinster styrs mycket av råvarupriser och blir därför
# ojämna, så bokfört värde och kassaflöde är stabilare ankare än P/E.
#
# Efterfrågade nyckeltal → verkligt substitut:
#   EV/EBITDA                        → finns direkt
#   Produktionskostnad per enhet     → Rörelsemarginal - lägre
#                                      produktionskostnad syns direkt som
#                                      högre marginal
#   Reserver/livslängd på tillgångar → Skuldsättningsgrad - reserv-/
#                                      livslängdsrisk är i grunden en fråga
#                                      om finansiell motståndskraft när
#                                      tillgångarna en dag sinar
#   Kassaflöde vid olika råvarupriser → Fritt kassaflöde-marginal (dagens
#                                      faktiska kassaflödesgenerering är
#                                      den bästa tillgängliga proxyn)
# ---------------------------------------------------------------------------
_COMMODITY_SCORING = [
    dict(_EV_EBITDA, ideal=6, scale=5, weight=0.20),
    {
        "key": "operating_margin",
        "label": "Rörelsemarginal (produktionskostnad-proxy)",
        "source": "operatingMargins",
        "type": "higher_better",
        "ideal": 0.28,
        "floor": 0.0,
        "weight": 0.20,
        "format": "{:.1%}",
        "positive_text": "Rörelsemarginalen på {value} tyder på låg produktionskostnad per enhet relativt intäkterna.",
        "negative_text": "Rörelsemarginalen på {value} tyder på hög produktionskostnad relativt intäkterna.",
    },
    dict(_FCF_MARGIN, ideal=0.12, floor=-0.10, weight=0.20,
         label="Fritt kassaflöde-marginal (råvaruprisscenario-proxy)"),
    {
        "key": "debt_to_equity",
        "label": "Skuldsättningsgrad (reservlivslängd-proxy)",
        "source": "debtToEquity",
        "type": "lower_better",
        "ideal": 60,
        "ceiling": 200,
        "weight": 0.13,
        "format": "{:.1f}",
        "positive_text": "Skuldsättningsgraden på {value} är sund, vilket ger motståndskraft när råvarupriser svänger eller tillgångar en dag sinar.",
        "negative_text": "Skuldsättningsgraden på {value} är hög, riskabelt när råvarupriser svänger.",
    },
    {
        "key": "revenue_growth",
        "label": "Omsättningstillväxt (YoY)",
        "source": "revenueGrowth",
        "type": "higher_better",
        "ideal": 0.12,
        "floor": -0.10,
        "weight": 0.10,
        "format": "{:.1%}",
        "positive_text": "Omsättningen växer med {value}.",
        "negative_text": "Omsättningen krymper ({value}), ofta ett tecken på svaga råvarupriser.",
    },
    dict(_FEAR_GREED_METRIC, weight=0.08),
    _MA200_METRIC,
]

_COMMODITY_INSIGHT = [
    _PROFIT_MARGIN_INSIGHT,
    _TARGET_UPSIDE_INSIGHT,
]


# ---------------------------------------------------------------------------
# TILLVÄXTBOLAG / TECH / SAAS (industry: Software - Application,
# Software - Infrastructure) - vinst är ofta liten eller negativ i utbyte
# mot tillväxt, så P/E och PEG blir missvisande. P/S och "Rule of 40"
# (tillväxt% + marginal%) är branschens egna standardmått.
#
# Efterfrågade nyckeltal → verkligt substitut:
#   P/S-tal                → finns (räknas ut, se _PRICE_TO_SALES)
#   Omsättningstillväxt    → finns direkt
#   Bruttomarginal         → finns direkt
#   Rule of 40             → räknas ut: tillväxt% + rörelsemarginal%
#   Kundretention/churn    → Fritt kassaflöde-marginal - churn syns inte i
#                            gratis-API:t, men ett SaaS-bolag med hög churn
#                            får svårt att nå ett sunt fritt kassaflöde
#                            eftersom det ständigt måste ersätta tappade
#                            kunder med dyr nykundsanskaffning
# ---------------------------------------------------------------------------
_SAAS_SCORING = [
    {
        "key": "revenue_growth",
        "label": "Omsättningstillväxt (YoY)",
        "source": "revenueGrowth",
        "type": "higher_better",
        "ideal": 0.30,
        "floor": -0.05,
        "weight": 0.23,
        "format": "{:.1%}",
        "positive_text": "Omsättningen växer med {value}, starkt för ett tillväxtbolag.",
        "negative_text": "Omsättningen växer svagt ({value}) för att vara ett tillväxtbolag.",
    },
    {
        "key": "gross_margin",
        "label": "Bruttomarginal",
        "source": "grossMargins",
        "type": "higher_better",
        "ideal": 0.75,
        "floor": 0.30,
        "weight": 0.18,
        "format": "{:.1%}",
        "positive_text": "Bruttomarginalen på {value} är stark, typiskt för ett skalbart mjukvarubolag.",
        "negative_text": "Bruttomarginalen på {value} är låg för ett mjukvarubolag.",
    },
    {
        "key": "rule_of_40",
        "label": "Rule of 40 (tillväxt + marginal)",
        "source": "computed:rule_of_40",
        "type": "higher_better",
        # 40+ räknas normalt som "godkänt" i SaaS-branschen - höjt till 55
        # för att bara riktigt starka tillväxt+lönsamhet-kombinationer ska
        # ge full pott här, inte bara "hyfsat balanserade" bolag.
        "ideal": 55,
        "floor": -20,
        "weight": 0.18,
        "format": "{:.0f}",
        "positive_text": "Rule of 40-värdet på {value} (tillväxt % + marginal %) visar en sund balans mellan tillväxt och lönsamhet.",
        "negative_text": "Rule of 40-värdet på {value} tyder på att varken tillväxten eller lönsamheten är tillräckligt stark just nu.",
    },
    dict(_PRICE_TO_SALES, ideal=8, ceiling=30, weight=0.13),
    dict(_FCF_MARGIN, ideal=0.18, floor=-0.15, weight=0.09,
         label="Fritt kassaflöde-marginal (kundretention-proxy)",
         positive_text="Fritt kassaflöde på {value} av omsättningen tyder på sund kundretention - inte bara dyr nykundsanskaffning.",
         negative_text="Fritt kassaflöde på {value} av omsättningen är svagt, vilket kan tyda på hög churn eller dyr tillväxt."),
    dict(_FEAR_GREED_METRIC, weight=0.09),
    _MA200_METRIC,
]

_SAAS_INSIGHT = [_PROFIT_MARGIN_INSIGHT, _DEFAULT_INSIGHT[1], _TARGET_UPSIDE_INSIGHT]


# ---------------------------------------------------------------------------
# INDUSTRI & TILLVERKNING (sector: Industrials) - kapitalintensiv,
# cyklisk verksamhet där EV/EBITDA och kassaflöde är viktigare än P/E.
#
# Efterfrågade nyckeltal → verkligt substitut:
#   EV/EBITDA                → finns direkt
#   Orderingång/orderstock   → Omsättningstillväxt - orderingång syns med
#                              viss eftersläpning i omsättningen, närmaste
#                              tillgängliga proxy
#   Rörelsemarginal (EBIT)   → finns direkt
#   Kapacitetsutnyttjande    → ROA - högt kapacitetsutnyttjande syns som
#                              hög avkastning på tillgångsbasen
#   Fritt kassaflöde         → finns (FCF-marginal)
# ---------------------------------------------------------------------------
_INDUSTRIALS_SCORING = [
    dict(_EV_EBITDA, ideal=9, scale=7, weight=0.22),
    {
        "key": "operating_margin",
        "label": "Rörelsemarginal (EBIT-marginal)",
        "source": "operatingMargins",
        "type": "higher_better",
        "ideal": 0.17,
        "floor": 0.0,
        "weight": 0.18,
        "format": "{:.1%}",
        "positive_text": "Rörelsemarginalen (EBIT) på {value} visar god operativ lönsamhet.",
        "negative_text": "Rörelsemarginalen (EBIT) på {value} är svag.",
    },
    {
        "key": "revenue_growth",
        "label": "Omsättningstillväxt (orderingång-proxy)",
        "source": "revenueGrowth",
        "type": "higher_better",
        "ideal": 0.12,
        "floor": -0.10,
        "weight": 0.18,
        "format": "{:.1%}",
        "positive_text": "Omsättningen växer med {value}, ett tecken på stark orderingång.",
        "negative_text": "Omsättningen krymper eller växer svagt ({value}), vilket kan tyda på svagare orderingång.",
    },
    dict(_ROA, ideal=0.09, weight=0.14,
         label="Avkastning på tillgångar (kapacitetsutnyttjande-proxy)"),
    dict(_FCF_MARGIN, ideal=0.10, floor=-0.05, weight=0.09),
    dict(_FEAR_GREED_METRIC, weight=0.09),
    _MA200_METRIC,
]

_INDUSTRIALS_INSIGHT = [_PROFIT_MARGIN_INSIGHT, _DEFAULT_INSIGHT[1], _TARGET_UPSIDE_INSIGHT]


# ---------------------------------------------------------------------------
# KONSUMENTBOLAG / DETALJHANDEL (industry: Specialty Retail, Internet
# Retail, Discount Stores, Grocery Stores, Apparel Retail, Home Improvement
# Retail) - marginaler och försäljningstillväxt driver avkastningen mer än
# klassisk värdering.
#
# Efterfrågade nyckeltal → verkligt substitut:
#   Bruttomarginal                        → finns direkt
#   Jämförbar försäljningstillväxt (LFL)  → Omsättningstillväxt - LFL
#                                          bryts inte ut i gratis-API:t,
#                                          total omsättningstillväxt är
#                                          närmaste proxy
#   Lageromsättningshastighet             → Kassalikviditet (current ratio)
#                                          - lagerdata finns inte separat,
#                                          men working capital-effektivitet
#                                          fångas delvis här
#   Rörelsemarginal (EBIT)                → finns direkt
# ---------------------------------------------------------------------------
_RETAIL_SCORING = [
    {
        "key": "revenue_growth",
        "label": "Omsättningstillväxt (jämförbar försäljning-proxy)",
        "source": "revenueGrowth",
        "type": "higher_better",
        "ideal": 0.10,
        "floor": -0.10,
        "weight": 0.28,
        "format": "{:.1%}",
        "positive_text": "Omsättningen växer med {value}, ett styrketecken för försäljningsutvecklingen.",
        "negative_text": "Omsättningen växer svagt eller krymper ({value}).",
    },
    {
        "key": "gross_margin",
        "label": "Bruttomarginal",
        "source": "grossMargins",
        "type": "higher_better",
        "ideal": 0.38,
        "floor": 0.10,
        "weight": 0.22,
        "format": "{:.1%}",
        "positive_text": "Bruttomarginalen på {value} är stark för handelsbranschen.",
        "negative_text": "Bruttomarginalen på {value} är svag för handelsbranschen.",
    },
    {
        "key": "operating_margin",
        "label": "Rörelsemarginal (EBIT-marginal)",
        "source": "operatingMargins",
        "type": "higher_better",
        "ideal": 0.10,
        "floor": 0.0,
        "weight": 0.22,
        "format": "{:.1%}",
        "positive_text": "Rörelsemarginalen på {value} visar god kostnadskontroll.",
        "negative_text": "Rörelsemarginalen på {value} är tunn, vanligt men riskabelt i handeln.",
    },
    {
        "key": "current_ratio",
        "label": "Kassalikviditet (lageromsättning-proxy)",
        "source": "currentRatio",
        "type": "higher_better",
        "ideal": 1.5,
        "floor": 0.7,
        "weight": 0.09,
        "format": "{:.2f}",
        "positive_text": "Kassalikviditeten på {value} tyder på god kontroll över lager och rörelsekapital.",
        "negative_text": "Kassalikviditeten på {value} är låg, vilket kan tyda på pressat rörelsekapital/lager.",
    },
    dict(_FEAR_GREED_METRIC, weight=0.09),
    _MA200_METRIC,
]

_RETAIL_INSIGHT = [_PROFIT_MARGIN_INSIGHT, _DEFAULT_INSIGHT[2], _TARGET_UPSIDE_INSIGHT]


# ---------------------------------------------------------------------------
# HÄLSOVÅRD (sector: Healthcare) - spänner från pre-vinst bioteknik (där
# kassan är allt som räknas) till etablerade lönsamma läkemedelsbolag, så
# skalan är byggd för att fungera rimligt åt båda hållen: P/S fungerar som
# värderingsanker oavsett om vinsten är negativ, medan tillväxt/marginal/
# skuldsättning fångar den underliggande kvaliteten.
#
# Efterfrågade nyckeltal → verkligt substitut:
#   Pipeline-värde                    → Omsättningstillväxt - pipeline-data
#                                       finns inte i gratis-API:t, men ett
#                                       lyckat pipeline-genombrott syns
#                                       förr eller senare som omsättning
#   FoU-kostnader (% av omsättning)   → P/S-tal + Vinstmarginal - FoU-andelen
#                                       rapporteras inte separat, men P/S
#                                       fungerar som värderingsanker när
#                                       vinsten är negativ (bioteknik), och
#                                       marginalen visar hur effektivt FoU:n
#                                       omsätts i lönsamhet för mer
#                                       etablerade bolag
#   Cash burn / runway                → Skuldsättningsgrad - kassa-runway
#                                       (se stock_sentiment) passar bäst för
#                                       renodlad bioteknik specifikt, men på
#                                       sektornivå fångar låg skuldsättning
#                                       samma underliggande motståndskraft
#   Patentcykel/exklusivitetsperioder → Skuldsättningsgrad
# ---------------------------------------------------------------------------
_HEALTHCARE_SCORING = [
    {
        "key": "revenue_growth",
        "label": "Omsättningstillväxt (pipeline-värde-proxy)",
        "source": "revenueGrowth",
        "type": "higher_better",
        "ideal": 0.15,
        "floor": -0.15,
        "weight": 0.25,
        "format": "{:.1%}",
        "positive_text": "Omsättningen växer med {value}, ett tecken på en produktiv pipeline.",
        "negative_text": "Omsättningen växer svagt eller krymper ({value}), vilket kan tyda på en tunn pipeline eller patentutgångar.",
    },
    dict(_PRICE_TO_SALES, ideal=6, ceiling=25, weight=0.22,
         label="P/S-tal (FoU-intensitet-proxy)"),
    {
        "key": "profit_margin",
        "label": "Vinstmarginal (FoU-effektivitet-proxy)",
        "source": "profitMargins",
        "type": "higher_better",
        "ideal": 0.18,
        # floor=0.0 (inte djupt negativt) - annars blir 0% vinstmarginal
        # (dvs INTE lönsam) orättvist högt betygsatt bara för att skalan
        # "räknar med" att många bioteknikbolag går ännu djupare back. Ett
        # bolag på exakt 0% ska bedömas lika strängt här som i alla andra
        # profiler i appen (~13 poäng), oavsett hur djupt förlustbolag i
        # samma bransch kan gå.
        "floor": 0.0,
        "weight": 0.21,
        "format": "{:.1%}",
        "positive_text": "Vinstmarginalen på {value} tyder på att FoU-satsningarna omsätts effektivt i lönsamhet.",
        "negative_text": "Vinstmarginalen på {value} är svag, vanligt för bolag i en tung FoU-fas men värt att hålla koll på.",
    },
    {
        "key": "debt_to_equity",
        "label": "Skuldsättningsgrad (patentrisk/runway-proxy)",
        "source": "debtToEquity",
        "type": "lower_better",
        "ideal": 40,
        "ceiling": 150,
        "weight": 0.13,
        "format": "{:.1f}",
        "positive_text": "Skuldsättningsgraden på {value} är låg, vilket ger motståndskraft om ett läkemedels exklusivitet tar slut eller kassan behöver räcka längre.",
        "negative_text": "Skuldsättningsgraden på {value} är hög, riskabelt kombinerat med patent-/finansieringsrisk.",
    },
    dict(_FEAR_GREED_METRIC, weight=0.09),
    _MA200_METRIC,
]

_HEALTHCARE_INSIGHT = [_TARGET_UPSIDE_INSIGHT, _DEFAULT_INSIGHT[1]]


# ---------------------------------------------------------------------------
# TELEKOM & INFRASTRUKTUR (industry: Telecom Services) - kapitalintensiv,
# skuldtung verksamhet med stabila men lågväxande intäkter. Ofta en
# utdelningssektor.
#
# Efterfrågade nyckeltal → verkligt substitut:
#   EV/EBITDA          → finns direkt
#   Capex/omsättning   → Fritt kassaflöde-marginal - capex-andelen
#                        rapporteras inte separat i gratis-API:t, men hög
#                        capex syns direkt som ett lägre fritt kassaflöde
#   Nettoskuld/EBITDA  → räknas ut (se _NET_DEBT_TO_EBITDA)
#   ARPU               → Direktavkastning - ARPU-data finns inte i
#                        gratis-API:t; direktavkastning är den mest
#                        relevanta tillgängliga proxyn för sektorns
#                        typiska "intäkt per investerad krona"-karaktär
# ---------------------------------------------------------------------------
_TELECOM_SCORING = [
    dict(_EV_EBITDA, ideal=7, scale=5, weight=0.20),
    dict(_NET_DEBT_TO_EBITDA, weight=0.25),
    dict(_FCF_MARGIN, ideal=0.14, floor=-0.05, weight=0.20,
         label="Fritt kassaflöde-marginal (capex/omsättning-proxy)"),
    dict(_DIVIDEND_YIELD_SCORING_HIGH, ideal=0.04, weight=0.08, label="Direktavkastning (ARPU-proxy)"),
    {
        "key": "revenue_growth",
        "label": "Omsättningstillväxt (YoY)",
        "source": "revenueGrowth",
        "type": "higher_better",
        "ideal": 0.06,
        "floor": -0.05,
        "weight": 0.10,
        "format": "{:.1%}",
        "positive_text": "Omsättningen växer med {value}.",
        "negative_text": "Omsättningen krymper ({value}), ovanligt för en mogen telekomverksamhet.",
    },
    dict(_FEAR_GREED_METRIC, weight=0.08),
    _MA200_METRIC,
]

_TELECOM_INSIGHT = [_PROFIT_MARGIN_INSIGHT, _DEFAULT_INSIGHT[1], _TARGET_UPSIDE_INSIGHT]


# ---------------------------------------------------------------------------
# TILLVÄXT/STABIL-VY - används av "Tillväxtbolag"/"Stabila bolag"-knapparna
# bredvid sökfältet. Byter INTE ut vilken profil/skala som väljs (Teknik har
# fortfarande sin skala, Fastigheter sin osv.) - viktar bara om nyckeltalen
# INOM den redan valda profilen, så att tydliga tillväxtbolag får högre
# betyg i tillväxtvyn, och tydligt stabila/lönsamma bolag får högre betyg
# i stabil-vyn. Se _apply_view_style i scoring.py för själva omviktningen.
#
# Varje nyckeltals "key" (samma namn oavsett vilken profil det förekommer
# i) taggas här som "growth" (gynnas i tillväxtvyn, straffas i stabil-vyn),
# "stability" (tvärtom) eller lämnas otaggad = neutral (samma vikt i båda
# vyerna - gäller marknadstimingmått som Fear & Greed/MA200 och PEG-talet,
# som redan är tillväxtjusterat och därför balanserat i grunden).
METRIC_STYLE = {
    "revenue_growth": "growth",
    "rule_of_40": "growth",
    "price_to_sales": "growth",
    "debt_to_equity": "stability",
    "operating_margin": "stability",
    "profit_margin": "stability",
    "dividend_yield": "stability",
    "roe": "stability",
    "roa": "stability",
    "pe_ratio": "stability",
    "gross_margin": "stability",
    "current_ratio": "stability",
    "price_to_book": "stability",
    "net_debt_to_ebitda": "stability",
    "fcf_margin": "stability",
    "ev_ebitda": "stability",
}


# Profilerna matchas bara på SEKTOR (Yahoos 11 huvudsektorer) - inte på de
# finare "industry"-nivåerna som tidigare (t.ex. Bank vs Investmentbolag,
# Biotech vs Pharma, SaaS-specifika mjukvarubranscher). Varje sektor har en
# egen skala; bolag utan matchande sektor hamnar i "Övrigt" (standard-
# skalan). Vill du gå tillbaka till finare branschindelning: lägg till
# "industry:<Yahoo-bransch>"-nycklar igen (de testas före sektor-nycklarna
# i scoring.py:s _select_profile).
PROFILES = {
    "default": {
        "label": "Övrigt",
        "scoring": _DEFAULT_SCORING,
        "insight": _DEFAULT_INSIGHT,
    },
    "sector:Industrials": {
        "label": "Industri",
        "scoring": _INDUSTRIALS_SCORING,
        "insight": _INDUSTRIALS_INSIGHT,
    },
    "sector:Technology": {
        "label": "Teknik",
        "scoring": _SAAS_SCORING,
        "insight": _SAAS_INSIGHT,
    },
    "sector:Financial Services": {
        "label": "Finans",
        "scoring": _BANK_SCORING,
        "insight": _BANK_INSIGHT,
    },
    "sector:Basic Materials": {
        "label": "Råvaror",
        "scoring": _COMMODITY_SCORING,
        "insight": _COMMODITY_INSIGHT,
    },
    "sector:Consumer Cyclical": {
        "label": "Konsument cyklisk",
        "scoring": _RETAIL_SCORING,
        "insight": _RETAIL_INSIGHT,
    },
    "sector:Real Estate": {
        "label": "Fastigheter",
        "scoring": _REAL_ESTATE_SCORING,
        "insight": _REAL_ESTATE_INSIGHT,
    },
    "sector:Communication Services": {
        "label": "Kommunikation",
        "scoring": _TELECOM_SCORING,
        "insight": _TELECOM_INSIGHT,
    },
    "sector:Consumer Defensive": {
        "label": "Konsumentstabil",
        "scoring": _RETAIL_SCORING,
        "insight": _RETAIL_INSIGHT,
    },
    "sector:Healthcare": {
        "label": "Hälsovård",
        "scoring": _HEALTHCARE_SCORING,
        "insight": _HEALTHCARE_INSIGHT,
    },
    "sector:Utilities": {
        "label": "Allmännyttigt",
        "scoring": _UTILITIES_SCORING,
        "insight": _UTILITIES_INSIGHT,
    },
    "sector:Energy": {
        "label": "Energi",
        "scoring": _COMMODITY_SCORING,
        "insight": _COMMODITY_INSIGHT,
    },
}

# Bakåtkompatibla namn - scoring.py kan falla tillbaka på dessa om en profil
# saknar egna listor (används inte just nu, men kostar inget att ha kvar).
SCORING_METRICS = _DEFAULT_SCORING
INSIGHT_METRICS = _DEFAULT_INSIGHT
