# Multi-agent M&A due diligence architecture and data sources

**Created:** 6/21/2026 18:09:05  
**Updated:** 6/21/2026 18:19:57  
**Exported:** 6/21/2026 22:47:24  
**Link:** [https://claude.ai/chat/9d834eac-a6a6-41d3-9d70-e5e897ef85ca](https://claude.ai/chat/9d834eac-a6a6-41d3-9d70-e5e897ef85ca)  

## Assistant:

> 6/21/2026 18:10:24

> Searched the web
>
> - MCP servers financial data SEC EDGAR public company data 2025
> - MCP server legal contracts compliance GitHub court records public data 2025
> - free public APIs financial data brand sentiment news company research due diligence 2025
> - OpenCorporates World Bank open government company data API patent database FDA public API due diligence
> - USPTO patent API public WIPO Google Patents API GitHub MCP 2025
> - **Done**

Good — I now have enough across all five agents. Let me compile a comprehensive, well-organized breakdown.

---

## M&A Due Diligence Agent System — Data Architecture & Ingestion Map

Here's a complete breakdown per agent: what data it needs, where to actually get it (free government sources first), and which MCP servers exist to wire it in.

---

### Agent A — Financial Auditor

**What it needs:** Balance sheets, income statements, cash flow, burn rate, debt, revenue trends.

**Free government source (primary):**

SEC EDGAR is the U.S. Securities and Exchange Commission's primary system for companies to submit official filings. It contains millions of filings and is a free public resource providing corporate financial information.

**MCP server for this:** `stefanoamorelli/sec-edgar-mcp` (pip-installable)

It exposes balance sheets, income statements, and cash flow via XBRL-parsed data, plus insider trading (Form 3/4/5 transactions). All responses include SEC filing URLs for verification.

The tools include `search_company` (by name or ticker, returns CIK), `get_financials` (structured data from latest 10-K/10-Q via XBRL), and `get_filings` (10-K, 10-Q, 8-K with dates and document links).

A second, more advanced option: `cyanheads/secedgar-mcp-server` supports

fetching SEC XBRL frames for one concept across all reporting companies, with annual, quarterly, and instant period support — useful for cross-company comparisons at scale.

**Supplementary free APIs (non-government):**

Alpha Vantage offers free stock APIs in JSON and CSV for real-time and historical stock market data, fundamental data, and 60+ technical and economic indicators. It also has an MCP server for AI agents and a market news/sentiment API.

Finnhub (free tier) is good for

a practical mix of quotes, news, sentiment signals, and market calendars with WebSocket streaming support.

Financial Modeling Prep (FMP) is the strongest for breadth:

fundamentals, transcripts, 13F filings, and technical indicators all in one API

— useful for validating research hypotheses before adding specialized sources.

**Ingestion pattern:** SEC EDGAR MCP → pandas agent reads XBRL-parsed JSON → detects churn via YoY revenue diffs, computes burn rate from cash flow, flags unusual debt-to-equity ratios.

---

### Agent B — Legal & Compliance

**What it needs:** Pending lawsuits, court records, federal regulations, contract red flags, compliance violations.

**Free government sources:**

For US court records: **CourtListener** (Free Law Project) — completely free, no subscription.

CourtListener covers oral arguments, financial disclosures, parties and attorneys, RECAP documents (full court filing access), advanced search across all data types, bulk data access, citation networks, precedent mapping, and bankruptcy data.

For US federal law/regulations: **GovInfo API** (free key from api.govinfo.gov) gives access to the US Code, Code of Federal Regulations (CFR), and the Federal Register.

For EU: **EUR-Lex** (no API key required) for GDPR, AI Act, and other EU regulations.

**MCP servers:**

`JamesANZ/us-legal-mcp` requires no API keys to start and connects to Congress bills, the Federal Register, and CourtListener court opinions simultaneously via a multi-source search.

`TCoder920x/open-legal-compliance-mcp` covers US federal law via GovInfo, US case law via CourtListener, and EU regulations via EUR-Lex scraping. Note that EUR-Lex, SEC EDGAR, and UK Legislation work without any API keys.

For deep court record access: `blakeox/courtlistener-mcp` is the most production-grade option —

it features intelligent LRU caching with legal-specific TTL strategies, automatic API rate limiting with queue management, and comprehensive CourtListener API v4 integration.

**Ingestion pattern:** Feed target company name → search CourtListener for active dockets → scan Federal Register for regulatory actions → RAG layer runs over retrieved documents to extract poison pills, indemnification clauses, liability caps.

---

### Agent C — Operations & Core Asset Evaluator

This agent splits by industry vertical. Here are the data endpoints per vertical:

**For IT/Software:** GitHub MCP (already in Claude's native tools) covers code quality, commit history, and open issues. Pair with `edgartools` for any capitalized software assets.

**For Pharma/Biotech — Patent Data:**

The `riemannzeta/patent_mcp_server` is a FastMCP server accessing USPTO data through the Patent Public Search API, Open Data Portal API, PTAB API v3, and Patent Litigation APIs. It has 52 tools and lets agents pull data from USPTO, search PTAB proceedings, analyze patent litigation, and research prosecution history.

Note on status:

As of March 20, 2026, the PatentsView API was shut down with data migrated to ODP bulk datasets. The Office Action and Enriched Citation APIs were also decommissioned in early 2026.

The PPUBS search and ODP tools still work.

For global patent coverage beyond USPTO:

The Google Patents API via Apify covers USPTO, EPO, WIPO, JPO, CN, KR and 100+ offices. It pulls claims, citations, family graphs, and CPC classifications, and has an MCP endpoint.

The EPO's Open Patent Services (OPS) API is the official free source for European patent data:

it gives programmatic access to bibliographic records, legal status data, patent family structures, and published document images from EPO and WIPO via INPADOC.

**For FDA compliance (Pharma):** FDA's public APIs at `api.fda.gov` are completely free and cover drug approvals, adverse events (FAERS), medical device reports, and enforcement actions — no key required for basic access.

**For Retail/Manufacturing:** World Bank Open Data API (free) and UN Comtrade (free tier) cover supply chain/trade flow data. BLS (Bureau of Labor Statistics) public API covers wage and labor data.

---

### Agent D — Brand & Market Sentiment

**What it needs:** News coverage, customer reviews, competitor positioning, social sentiment.

**Free/freemium sources:**

Alpha Vantage has a market news API with sentiment scores powered by AI and machine learning, covering any ticker or topic.

The GDELT Project is a free academic-commercial hybrid that monitors global news media across print, broadcast, and web sources to identify patterns in world events.

It's completely free and accessible via BigQuery or direct download.

For structured news sentiment by ticker, **Finnhub's** news-sentiment endpoint is free-tier accessible. For review data, the Google Places API (free tier) and Yelp Fusion API cover consumer-facing businesses.

**Ingestion pattern:** Web search MCP → retrieve last 90 days of news mentions → GDELT API for sentiment time-series → alpha vantage NEWS_SENTIMENT endpoint by ticker → aggregate into bearish/bullish signal with flagged keywords (layoffs, lawsuit, recall, fraud).

---

### Cross-Agent: Global Company Identity Layer

Before any agent starts, you need to resolve the target company to a verified legal entity. This is where:

OpenCorporates has over 200 million companies from primary public sources, all with full provenance.

The API supports company search by name, retrieval of officers, filings, and registrations — covering companies across jurisdictions worldwide.

OpenCorporates' officer search is essential: you can search by officer name and see all companies that person is related to across all jurisdictions they cover — critical for due diligence and uncovering hidden affiliations.

Free tier: 500 API calls/month. For a Kaggle project with a fixed target company set this is fine.

---

### Architecture Summary (Plain Text)

```
INPUT: Company name / ticker
    ↓
[Entity Resolution Layer]
    OpenCorporates API → canonical legal entity, jurisdiction, registration status

    ↓ feeds all 4 agents in parallel

[Financial Auditor]
    SEC EDGAR MCP (10-K, 10-Q, 8-K, XBRL) → pandas analysis
    Alpha Vantage / FMP / Finnhub → supplementary ratios

[Legal & Compliance]
    CourtListener MCP → active dockets, opinions
    GovInfo API → CFR/US Code compliance checks
    EUR-Lex (no key) → EU regulatory exposure

[Operations Evaluator]
    IT:     GitHub MCP → code/tech debt
    Pharma: USPTO Patent MCP + EPO OPS API + FDA API
    Retail: UN Comtrade + BLS API

[Brand & Sentiment]
    Alpha Vantage NEWS_SENTIMENT + GDELT → time-series sentiment
    Web search MCP → recent coverage
    Google Places / Yelp → consumer reviews

    ↓
[Orchestrator / Synthesis Agent]
    Aggregates agent outputs → risk score + flag summary → final report
```

---

### Key Architectural Concerns to Address

**Data freshness mismatch:** SEC EDGAR filings are quarterly; GDELT news is real-time. Your synthesis layer needs to timestamp-weight signals — a bad Q4 filing matters less if Q1 news is bullish recovery.

**Rate limits on free tiers:** OpenCorporates is 500 calls/month, Alpha Vantage free is 25 calls/day. For Kaggle evaluation, pre-cache target company data in CSVs rather than hitting live APIs per query — especially for the financial agent.

**Private companies:** SEC EDGAR only covers US public companies. For private M&A targets, you'll need OpenCorporates + manual CSV ingestion. Flag this scope limitation explicitly in your project write-up.

**RAG for Legal Agent:** The legal agent's contract scanning (poison pills, liability clauses) needs a local RAG layer. The MCP servers give you court data, but the target's own contracts live in Google Drive or a file vault — that's where the Drive MCP connector comes in for the internal document side.

This is a genuinely strong capstone project concept. The SEC EDGAR MCP + CourtListener + USPTO patent MCP combination alone gives you a solid all-public-data foundation that most commercial due diligence platforms charge thousands for.

---

**Sources:**

- [sec-edgar-mcp – Apis And Http Requests MCP Server by Stefanoamorelli Model Context Protocol Tool | Free DevTools by Hexmos](https://hexmos.com/freedevtools/mcp/apis-and-http-requests/stefanoamorelli--sec-edgar-mcp/)
- [sec-edgar-mcp · PyPI](https://pypi.org/project/sec-edgar-mcp/)
- [GitHub - leopoldodonnell/edgar-mcp: SEC EDGAR MCP Server - A Model Context Protocol server for accessing SEC EDGAR data · GitHub](https://github.com/leopoldodonnell/edgar-mcp)
- [GitHub - stefanoamorelli/sec-edgar-mcp: A SEC EDGAR MCP (Model Context Protocol) Server · GitHub](https://github.com/stefanoamorelli/sec-edgar-mcp)
- [Sec Edgar Mcp: 6 Tools | MCP Servers](https://claudemarketplaces.com/mcp/stefanoamorelli/sec-edgar-mcp)
- [GitHub - cyanheads/secedgar-mcp-server: Query SEC EDGAR filings, XBRL financials, and company data through MCP. STDIO & Streamable HTTP. · GitHub](https://github.com/cyanheads/secedgar-mcp-server)
- [EdgarTools MCP for SEC Filings](https://www.edgartools.io/edgartools-mcp-for-sec-filings/)
- [SEC EDGAR MCP Server by Stefano Amorelli | PulseMCP](https://www.pulsemcp.com/servers/sec-edgar)
- [GitHub - agentic-ops/legal-mcp: A comprehensive MCP Server for legal workflows - seeking legal professionals for case study collaboration · GitHub](https://github.com/agentic-ops/legal-mcp)
- [GitHub - JamesANZ/us-legal-mcp: An MCP server that provides comprehensive US legislation. · GitHub](https://github.com/JamesANZ/us-legal-mcp)
- [GitHub - TCoder920x/open-legal-compliance-mcp: Model Context Protocol server for legal compliance analysis using free/open government APIs · GitHub](https://github.com/TCoder920x/open-legal-compliance-mcp)
- [GitHub - blakeox/courtlistener-mcp: An MCP server that bridges Anthropic’s Claude (and other LLMs) with the CourtListener API for live legal data—opinions, dockets, court records, and more. Designed to power legal research and compliance tools with transparency, reliability, and fewer hallucinations. Scalable, open, and easy to extend.](https://github.com/blakeox/courtlistener-mcp)
- [Court Records MCP | Awesome MCP Servers](https://mcpservers.org/servers/github-com-martc03-gov-mcp-servers-tree-main-servers-court-records-mcp)
- [Open Legal Compliance MCP Server | M...](https://lobehub.com/mcp/tcoder920x-open-legal-compliance-mcp)
- [GitHub - Travis-Prall/court-listener-mcp · GitHub](https://github.com/Travis-Prall/court-listener-mcp)
- [GitHub - Mahender22/legal-mcp: The first comprehensive US legal MCP server -- case law, citations, practice management, and court filings for AI assistants · GitHub](https://github.com/Mahender22/legal-mcp)
- [GitHub - DefendTheDisabled/courtlistener-mcp: An MCP (Model Context Protocol) server providing AI agents access to CourtListener's comprehensive legal database, featuring semantic search, hybrid search, citation verification, and research tools. · GitHub](https://github.com/DefendTheDisabled/courtlistener-mcp)
- [Free Stock Market API and Financial Statements API... | FMP](https://site.financialmodelingprep.com/developer/docs)
- [API Documentation | Finnhub - Free APIs for realtime stock, forex, and cryptocurrency. Company fundamentals, economic data, and alternative data.](https://finnhub.io/docs/api/news-sentiment)
- [Free Stock APIs in JSON & Excel | Alpha Vantage](https://www.alphavantage.co/)
- [Finnhub Stock APIs - Real-time stock prices, Company fundamentals, Estimates, and Alternative data.](https://finnhub.io/)
- [OSINT Tools And Techniques | OSINT Technical Sources](https://www.neotas.com/osint-tools-and-techniques/)
- [Financial News Feed and Stock News Sentiment data API | EODHD APIs Documentation](https://eodhd.com/financial-apis/stock-market-financial-news-api)
- [The Best Alternative Data APIs for Financial Insight](https://webz.io/blog/news-api/the-best-alternative-data-apis-for-financial-insight/)
- [7 Best Investment Research APIs for AI-First Use Cases in 2026](https://www.firecrawl.dev/blog/best-investment-research-apis)
- [The 12 Best Financial Analysis Software Platforms for 2025 – visbanking.com](https://visbanking.com/best-financial-analysis-software)
- [Best Financial Data APIs in 2026](https://www.nb-data.com/p/best-financial-data-apis-in-2026)
- [OpenCorporates API](https://api.opencorporates.com/)
- [API Reference: version 0.4.8 :: OpenCorporates API](https://api.opencorporates.com/documentation/API-Reference)
- [Getting started with the OpenCorporates API: A beginner’s guide](https://blog.opencorporates.com/2025/02/13/getting-started-with-the-opencorporates-api/)
- [8 OpenCorporates Alternatives for KYB & Company Registry Lookup - Zephira.ai](https://zephira.ai/8-opencorporates-alternatives-for-kyb-company-registry-lookup/)
- [5 ways to use the OpenCorporates API to power your critical business processes – OpenCorporates](https://blog.opencorporates.com/2022/08/04/5-ways-to-use-the-opencorporates-api-to-power-your-critical-business-processes/)
- [Step-by-step guide for using OpenCorporates data in entity verification – OpenCorporates](https://blog.opencorporates.com/2024/11/28/opencorporates-data-in-entity-verification/)
- [OpenCorporates Transforms for Maltego](https://www.maltego.com/transform-hub/opencorporates/)
- [OpenCorporates API - PublicAPI](https://publicapi.dev/open-corporates-api)
- [Plug in : Open Corporates](https://opencorporates.com/plug-in-our-data/)
- [A Beginner’s Guide to Using the OpenCorporates API to Power Your Investigation](https://tcij.org/summer-conference-event/a-beginners-guide-to-using-the-opencorporates-api-to-power-your-investigation/)
- [GitHub - riemannzeta/patent_mcp_server: FastMCP Server for USPTO data · GitHub](https://github.com/riemannzeta/patent_mcp_server)
- [Google Patents Scraper API - MCP, Claude AI · Apify](https://apify.com/johnvc/google-patents-api)
- [Top 4 Patent Search APIs for Developers and Innovation Teams - PQAI](https://projectpq.ai/best-patent-search-apis/)
- [API - Search - Open Data Portal - USPTO](https://data.uspto.gov/apis/patent-file-wrapper/search)
- [Home | Open Data Portal](https://developer.uspto.gov/api-catalog)
- [Chapter 7 Databases | The WIPO Manual on Open Source Patent Analytics (2nd edition)](https://wipo-analytics.github.io/manual/databases.html)
- [Chapter 5 Databases | The WIPO Manual on Open Source Patent Analytics: First Edition](https://wipo-analytics.github.io/manualv1/databases.html)
- [GitHub - YobieBen/uspto-crawler-mcp: USPTO Patent & Trademark Web Crawler with Crawl4AI and MCP integration · GitHub](https://github.com/YobieBen/uspto-crawler-mcp)
- [USPTO API - Patent & Trademark Data MCP server · Apify](https://apify.com/alizarin_refrigerator-owner/uspto-api---patent-trademark-data/api/mcp)
- [Add Patent Search Tool · Issue #78 · zoharbabin/google-researcher-mcp](https://github.com/zoharbabin/google-researcher-mcp/issues/78)

Powered by Claude Exporter (https://www.ai-chat-exporter.net)
