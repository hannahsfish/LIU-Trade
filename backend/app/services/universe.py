"""
US large-cap stock universe for LEI scanner.
~200 stocks: S&P 500 core components across all sectors.
Manually curated to exclude financials/REITs/utilities (LEI focuses on growth).
"""

SCAN_UNIVERSE: list[str] = [
    # Technology
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO",
    "ORCL", "CRM", "AMD", "ADBE", "CSCO", "ACN", "INTC", "IBM",
    "QCOM", "TXN", "INTU", "AMAT", "NOW", "PANW", "SNPS", "CDNS",
    "KLAC", "LRCX", "MRVL", "ADI", "NXPI", "FTNT", "CRWD", "TEAM",
    "WDAY", "ZS", "DDOG", "NET", "MDB", "SNOW", "PLTR", "SHOP",
    "SQ", "COIN", "TTD", "HUBS", "VEEV", "ANSS", "KEYS", "MPWR",
    "ON", "SMCI", "ARM", "MELI",

    # Healthcare
    "UNH", "LLY", "JNJ", "ABBV", "MRK", "TMO", "ABT", "DHR",
    "PFE", "AMGN", "BMY", "ISRG", "GILD", "VRTX", "MDT", "SYK",
    "REGN", "BSX", "ZTS", "EW", "DXCM", "IDXX", "IQV", "ALGN",
    "MRNA", "BIIB", "ILMN", "HOLX", "PODD", "INCY",

    # Consumer Discretionary
    "HD", "MCD", "NKE", "LOW", "SBUX", "TJX", "BKNG", "CMG",
    "ABNB", "ORLY", "AZO", "ROST", "DHI", "LEN", "GM", "F",
    "LULU", "DECK", "ULTA", "POOL", "DPZ", "YUM", "DARDEN",

    # Consumer Staples
    "PG", "KO", "PEP", "COST", "WMT", "PM", "MO", "CL",
    "MNST", "STZ", "KHC", "GIS", "HSY", "KDP", "EL",

    # Industrials
    "CAT", "RTX", "HON", "UNP", "UPS", "BA", "DE", "GE",
    "LMT", "NOC", "GD", "MMM", "ITW", "EMR", "ETN", "ROK",
    "PH", "IR", "AME", "FAST", "CTAS", "ODFL", "URI", "CARR",
    "VRSK", "WAB", "TT", "XYL",

    # Communication Services
    "GOOG", "DIS", "NFLX", "CMCSA", "T", "VZ", "TMUS",
    "EA", "ATVI", "RBLX", "MTCH", "ZM", "PINS", "SNAP",

    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX",
    "VLO", "OXY", "DVN", "HAL", "FANG",

    # Materials
    "LIN", "APD", "SHW", "ECL", "FCX", "NEM", "NUE",
    "DOW", "DD", "PPG", "VMC", "MLM",
]

SECTOR_MAP: dict[str, str] = {
    "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
    "AMZN": "Technology", "NVDA": "Technology", "META": "Technology",
    "TSLA": "Consumer Discretionary", "UNH": "Healthcare", "LLY": "Healthcare",
    "JNJ": "Healthcare", "XOM": "Energy", "HD": "Consumer Discretionary",
}


def get_universe() -> list[str]:
    return SCAN_UNIVERSE.copy()


def get_universe_size() -> int:
    return len(SCAN_UNIVERSE)
