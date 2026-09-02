"""
Översättningar av Yahoo Finances bransch-klassificering till svenska.

Yahoo klassificerar varje bolag i en bred SEKTOR (bara 11 möjliga värden -
alla täcks här) och en snävare BRANSCH ("industry", hundratals möjliga
värden - de vanligaste täcks här). Saknas en bransch-översättning visar vi
sektorns svenska namn istället, så du i praktiken aldrig ser rå engelska
på sidan.

Stöter du på ett bolag med en bransch som inte täcks: lägg till en rad i
INDUSTRY_TRANSLATIONS nedan med Yahoos engelska namn (syns i terminalen om
du kör `python -c "from yahoo_client import get_info; print(get_info('TICKER')['industry'])"`)
som nyckel och din svenska översättning som värde.
"""

SECTOR_TRANSLATIONS = {
    "Technology": "Teknik",
    "Financial Services": "Finans",
    "Healthcare": "Hälsovård",
    "Consumer Cyclical": "Konsument cyklisk",
    "Consumer Defensive": "Konsumentstabil",
    "Industrials": "Industri",
    "Energy": "Energi",
    "Utilities": "Allmännyttigt",
    "Real Estate": "Fastigheter",
    "Basic Materials": "Råvaror",
    "Communication Services": "Kommunikation",
}

INDUSTRY_TRANSLATIONS = {
    # Teknik
    "Software - Infrastructure": "Mjukvara - Infrastruktur",
    "Software - Application": "Mjukvara - Applikationer",
    "Semiconductors": "Halvledare",
    "Semiconductor Equipment & Materials": "Halvledarutrustning & material",
    "Consumer Electronics": "Konsumentelektronik",
    "Electronic Components": "Elektronikkomponenter",
    "Information Technology Services": "IT-tjänster",
    "Computer Hardware": "Datorhårdvara",
    "Communication Equipment": "Kommunikationsutrustning",
    "Scientific & Technical Instruments": "Vetenskapliga & tekniska instrument",
    "Solar": "Solenergi",

    # Finans
    "Asset Management": "Kapitalförvaltning",
    "Banks - Diversified": "Banker - Diversifierade",
    "Banks - Regional": "Banker - Regionala",
    "Insurance - Diversified": "Försäkring - Diversifierad",
    "Insurance - Life": "Försäkring - Liv",
    "Insurance - Property & Casualty": "Försäkring - Sak",
    "Insurance - Specialty": "Försäkring - Specialiserad",
    "Insurance Brokers": "Försäkringsmäklare",
    "Credit Services": "Kreditbolag",
    "Capital Markets": "Kapitalmarknader",
    "Financial Data & Stock Exchanges": "Finansiell data & börser",
    "Financial Conglomerates": "Finanskonglomerat",
    "Mortgage Finance": "Bolånefinansiering",
    "Shell Companies": "Skalbolag",

    # Hälsovård
    "Drug Manufacturers - General": "Läkemedelstillverkare - Generell",
    "Drug Manufacturers - Specialty & Generic": "Läkemedelstillverkare - Special & generika",
    "Biotechnology": "Bioteknik",
    "Medical Devices": "Medicinteknik",
    "Medical Instruments & Supplies": "Medicinska instrument & förbrukningsvaror",
    "Diagnostics & Research": "Diagnostik & forskning",
    "Healthcare Plans": "Sjukvårdsförsäkring",
    "Medical Care Facilities": "Vårdinrättningar",
    "Medical Distribution": "Medicinsk distribution",
    "Pharmaceutical Retailers": "Apotekskedjor",

    # Sällanköpsvaror
    "Internet Retail": "Näthandel",
    "Specialty Retail": "Fackhandel",
    "Auto Manufacturers": "Biltillverkare",
    "Auto Parts": "Bildelar",
    "Restaurants": "Restauranger",
    "Apparel Retail": "Klädhandel",
    "Apparel Manufacturing": "Klädtillverkning",
    "Footwear & Accessories": "Skor & accessoarer",
    "Home Improvement Retail": "Byggvaruhandel",
    "Leisure": "Fritid & nöje",
    "Resorts & Casinos": "Semesteranläggningar & kasinon",
    "Travel Services": "Reseföretag",
    "Lodging": "Hotell",
    "Furnishings, Fixtures & Appliances": "Möbler, inredning & vitvaror",
    "Luxury Goods": "Lyxvaror",
    "Auto & Truck Dealerships": "Bil- & lastbilshandel",
    "Recreational Vehicles": "Fritidsfordon",
    "Gambling": "Spelbolag",

    # Dagligvaror
    "Discount Stores": "Lågpriskedjor",
    "Grocery Stores": "Livsmedelsbutiker",
    "Packaged Foods": "Förpackade livsmedel",
    "Beverages - Non-Alcoholic": "Drycker - Alkoholfria",
    "Beverages - Wineries & Distilleries": "Drycker - Vin & sprit",
    "Beverages - Brewers": "Drycker - Bryggerier",
    "Household & Personal Products": "Hushålls- & hygienprodukter",
    "Tobacco": "Tobak",
    "Farm Products": "Jordbruksprodukter",
    "Education & Training Services": "Utbildningstjänster",

    # Industri
    "Farm & Heavy Construction Machinery": "Jordbruks- & anläggningsmaskiner",
    "Aerospace & Defense": "Flyg & försvar",
    "Airlines": "Flygbolag",
    "Airports & Air Services": "Flygplatser & flygtjänster",
    "Railroads": "Järnväg",
    "Marine Shipping": "Sjöfart",
    "Trucking": "Åkeri & lastbilstransport",
    "Integrated Freight & Logistics": "Integrerad frakt & logistik",
    "Building Products & Equipment": "Byggprodukter & -utrustning",
    "Engineering & Construction": "Ingenjörsverksamhet & bygg",
    "Specialty Industrial Machinery": "Specialiserade industrimaskiner",
    "Industrial Distribution": "Industridistribution",
    "Business Equipment & Supplies": "Kontorsutrustning & -material",
    "Staffing & Employment Services": "Bemanning & rekrytering",
    "Consulting Services": "Konsulttjänster",
    "Security & Protection Services": "Säkerhetstjänster",
    "Waste Management": "Avfallshantering",
    "Pollution & Treatment Controls": "Miljöteknik & rening",
    "Electrical Equipment & Parts": "Elutrustning & -delar",
    "Conglomerates": "Konglomerat",
    "Tools & Accessories": "Verktyg & tillbehör",
    "Metal Fabrication": "Metallbearbetning",
    "Rental & Leasing Services": "Uthyrning & leasing",
    "Specialty Business Services": "Specialiserade företagstjänster",

    # Energi
    "Oil & Gas E&P": "Olja & gas - Prospektering & utvinning",
    "Oil & Gas Integrated": "Olja & gas - Integrerat",
    "Oil & Gas Midstream": "Olja & gas - Midstream",
    "Oil & Gas Refining & Marketing": "Olja & gas - Raffinering",
    "Oil & Gas Equipment & Services": "Olja & gas - Utrustning & tjänster",
    "Oil & Gas Drilling": "Olja & gas - Borrning",
    "Thermal Coal": "Termiskt kol",
    "Uranium": "Uran",

    # Kraftförsörjning
    "Utilities - Regulated Electric": "Kraftförsörjning - Reglerad el",
    "Utilities - Regulated Gas": "Kraftförsörjning - Reglerad gas",
    "Utilities - Regulated Water": "Kraftförsörjning - Reglerat vatten",
    "Utilities - Diversified": "Kraftförsörjning - Diversifierad",
    "Utilities - Renewable": "Kraftförsörjning - Förnybar",
    "Utilities - Independent Power Producers": "Kraftförsörjning - Oberoende kraftproducenter",

    # Fastigheter
    "REIT - Residential": "REIT - Bostäder",
    "REIT - Office": "REIT - Kontor",
    "REIT - Retail": "REIT - Handel",
    "REIT - Industrial": "REIT - Industri",
    "REIT - Healthcare Facilities": "REIT - Vårdfastigheter",
    "REIT - Hotel & Motel": "REIT - Hotell",
    "REIT - Diversified": "REIT - Diversifierad",
    "REIT - Specialty": "REIT - Specialiserad",
    "REIT - Mortgage": "REIT - Bolån",
    "Real Estate Services": "Fastighetstjänster",
    "Real Estate - Development": "Fastighetsutveckling",
    "Real Estate - Diversified": "Fastigheter - Diversifierad",

    # Material
    "Specialty Chemicals": "Specialkemikalier",
    "Chemicals": "Kemikalier",
    "Agricultural Inputs": "Jordbruksinsatsvaror",
    "Building Materials": "Byggmaterial",
    "Steel": "Stål",
    "Gold": "Guld",
    "Silver": "Silver",
    "Copper": "Koppar",
    "Aluminum": "Aluminium",
    "Other Industrial Metals & Mining": "Övriga industrimetaller & gruvdrift",
    "Other Precious Metals & Mining": "Övriga ädelmetaller & gruvdrift",
    "Paper & Paper Products": "Papper & pappersprodukter",
    "Lumber & Wood Production": "Trävaror & träproduktion",
    "Coking Coal": "Koks & kol",
    "Packaging & Containers": "Förpackningar",

    # Kommunikationstjänster
    "Internet Content & Information": "Internetinnehåll & information",
    "Telecom Services": "Telekomtjänster",
    "Entertainment": "Underhållning",
    "Broadcasting": "Sändningsmedia",
    "Publishing": "Förlagsverksamhet",
    "Electronic Gaming & Multimedia": "Datorspel & multimedia",
    "Advertising Agencies": "Reklambyråer",
}


def translate_sector(sector: str) -> str:
    return SECTOR_TRANSLATIONS.get(sector, sector or "")


def translate_industry(industry: str, sector: str) -> str:
    """Ger en svensk etikett för Yahoos bransch-klassificering. Faller
    tillbaka på sektorns svenska namn om branschen inte finns i listan
    ovan, och sist på originaltexten (engelska) om inget alls är känt."""
    if industry and industry in INDUSTRY_TRANSLATIONS:
        return INDUSTRY_TRANSLATIONS[industry]
    if sector:
        return translate_sector(sector)
    return industry or ""
