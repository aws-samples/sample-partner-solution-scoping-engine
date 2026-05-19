# SERA — Open Source Package Inventory (OSPI)

**Generated:** 2026-04-24
**Application:** SERA (Solutions Engine for Recommending AWS)
**Version:** 0.1.0
**Prepared by:** Tsvetko Tsenkov

---

## Summary

| Category | Count | Pre-Approved | Needs IP Review |
|----------|-------|-------------|-----------------|
| Python (Backend + MCP Servers) | 54 | 54 | 0 |
| Node.js (Frontend) | 23 | 23 | 0 |
| **Total** | **77** | **77** | **0** |

All 77 packages use pre-approved licenses. No IP review is required.

- **fpdf2 (LGPL-3.0-only)** — Used as an unmodified dependency by the SOW Generator MCP server. LGPL-3.0 is pre-approved for unmodified redistribution.
- **python-dateutil (Apache-2.0 OR BSD)** — Dual-licensed under two permissive, pre-approved licenses. Apache-2.0 selected for attribution.

---

## License Distribution

| License | Count | Type |
|---------|-------|------|
| MIT | 43 | Permissive |
| Apache-2.0 | 18 | Permissive |
| BSD-3-Clause | 9 | Permissive |
| BSD (unspecified) | 4 | Permissive |
| BSD-2-Clause | 2 | Permissive |
| PSF-2.0 | 1 | Permissive |
| MIT-CMU | 1 | Permissive |
| LGPL-3.0-only | 1 | Weak Copyleft (unmodified) |
| Apache-2.0 OR BSD | 1 | Permissive (dual-licensed) |

---

## Python Packages (Backend + MCP Servers)

| # | Package | Version | License | Source |
|---|---------|---------|---------|--------|
| 1 | aiohttp | 3.13.5 | Apache-2.0 AND MIT | Backend, WA Framework MCP |
| 2 | authlib | 1.7.0 | BSD-3-Clause | Backend |
| 3 | bandit | 1.9.4 | Apache-2.0 | CloudFormation MCP, Diagram MCP |
| 4 | black | 26.3.1 | MIT | Backend |
| 5 | boto3 | 1.42.96 | Apache-2.0 | Backend, all MCP servers |
| 6 | botocore | 1.42.96 | Apache-2.0 | Funding Reviewer MCP, CloudFormation MCP |
| 7 | bs4 | 0.0.2 | MIT | Cost Analysis MCP, Service Validation MCP |
| 8 | cachetools | 7.0.6 | MIT | Backend, Pricing Calculator MCP |
| 9 | checkov | 3.2.524 | Apache-2.0 | CloudFormation MCP |
| 10 | cryptography | 47.0.0 | Apache-2.0 OR BSD-3-Clause | Backend |
| 11 | diagrams | 0.25.1 | MIT | Diagram MCP |
| 12 | fastapi | 0.136.1 | MIT | Funding Reviewer MCP |
| 13 | fastmcp | 3.2.4 | Apache-2.0 | Backend |
| 14 | flake8 | 7.3.0 | MIT | Backend |
| 15 | Flask | 3.1.3 | BSD-3-Clause | Backend |
| 16 | flask-cors | 6.0.2 | MIT | Backend |
| 17 | Flask-Session | 0.8.0 | BSD | Backend |
| 18 | Flask-SQLAlchemy | 3.1.1 | BSD | Backend |
| 19 | Flask-WTF | 1.3.0 | BSD | Backend |
| 20 | fpdf2 | 2.8.7 | LGPL-3.0-only | SOW Generator MCP |
| 21 | gunicorn | 25.3.0 | MIT | Backend |
| 22 | httpx | 0.28.1 | BSD-3-Clause | Service Validation MCP |
| 23 | Jinja2 | 3.1.6 | BSD | SOW Generator MCP, WA Framework MCP |
| 24 | jschema-to-python | 1.2.3 | MIT | CloudFormation MCP, Diagram MCP |
| 25 | loguru | 0.7.3 | MIT | Cost Analysis MCP, Service Validation MCP, APN Funding MCP |
| 26 | markdown2 | 2.5.5 | MIT | SOW Generator MCP |
| 27 | Markdown2docx | 0.1.0 | MIT | SOW Generator MCP |
| 28 | mcp | 1.27.0 | MIT | All MCP servers |
| 29 | nova-act | 3.3.316.0 | Apache-2.0 | Backend |
| 30 | pillow | 12.2.0 | MIT-CMU | Funding Reviewer MCP |
| 31 | psutil | 7.2.2 | BSD-3-Clause | Funding Reviewer MCP, WA Framework MCP |
| 32 | pydantic | 2.13.3 | MIT | All MCP servers |
| 33 | PyJWT | 2.12.1 | MIT | Backend |
| 34 | PyMySQL | 1.1.2 | MIT | Backend |
| 35 | pypdf | 6.10.2 | BSD-3-Clause | Funding Reviewer MCP |
| 36 | pyright | 1.1.409 | MIT | WA Framework MCP |
| 37 | pytest | 9.0.3 | MIT | Backend, multiple MCP servers |
| 38 | pytest-asyncio | 1.3.0 | Apache-2.0 | Multiple MCP servers |
| 39 | pytest-cov | 7.1.0 | MIT | Backend |
| 40 | python-dateutil | 2.9.0.post0 | Apache-2.0 OR BSD | SOW Generator MCP |
| 41 | python-docx | 1.2.0 | MIT | Funding Reviewer MCP, WA Framework MCP |
| 42 | python-dotenv | 1.2.2 | BSD-3-Clause | Backend |
| 43 | PyYAML | 6.0.3 | MIT | CloudFormation MCP, WA Framework MCP |
| 44 | redis | 7.4.0 | MIT | Backend |
| 45 | reportlab | 4.4.10 | BSD | Funding Reviewer MCP |
| 46 | requests | 2.33.1 | Apache-2.0 | Backend, Funding Reviewer MCP |
| 47 | requests-auth-aws-sigv4 | 0.7 | Apache-2.0 | Backend |
| 48 | ruff | 0.15.12 | MIT | WA Framework MCP |
| 49 | sarif-om | 1.0.4 | MIT | CloudFormation MCP, Diagram MCP |
| 50 | selenium | 4.43.0 | Apache-2.0 | Backend |
| 51 | typing-extensions | 4.15.0 | PSF-2.0 | Multiple MCP servers |
| 52 | uvicorn | 0.46.0 | BSD-3-Clause | Funding Reviewer MCP |
| 53 | watchtower | 3.4.0 | Apache-2.0 | Backend |
| 54 | webdriver-manager | 4.0.2 | Apache-2.0 | Backend |

---

## Node.js Packages (Frontend)

| # | Package | Version | License | Type |
|---|---------|---------|---------|------|
| 1 | @cloudscape-design/components | 3.0.1284 | Apache-2.0 | dependency |
| 2 | @cloudscape-design/design-tokens | 3.0.83 | Apache-2.0 | dependency |
| 3 | @cloudscape-design/global-styles | 1.0.57 | Apache-2.0 | dependency |
| 4 | @eslint/js | 10.0.1 | MIT | devDependency |
| 5 | @types/react | 19.2.14 | MIT | devDependency |
| 6 | @types/react-dom | 19.2.3 | MIT | devDependency |
| 7 | @vitejs/plugin-react | 6.0.1 | MIT | devDependency |
| 8 | compression | 1.8.1 | MIT | override |
| 9 | eslint | 10.2.1 | MIT | devDependency |
| 10 | eslint-plugin-react-hooks | 7.1.1 | MIT | devDependency |
| 11 | eslint-plugin-react-refresh | 0.5.2 | MIT | devDependency |
| 12 | globals | 17.5.0 | MIT | devDependency |
| 13 | mammoth | 1.12.0 | BSD-2-Clause | dependency |
| 14 | on-headers | 1.1.0 | MIT | override |
| 15 | react | 19.2.5 | MIT | dependency |
| 16 | react-dom | 19.2.5 | MIT | dependency |
| 17 | react-markdown | 10.1.0 | MIT | dependency |
| 18 | react-router-dom | 7.14.2 | MIT | dependency |
| 19 | remark-gfm | 4.0.1 | MIT | dependency |
| 20 | sass-embedded | 1.99.0 | MIT | devDependency |
| 21 | serve | 14.2.6 | MIT | dependency |
| 22 | terser | 5.46.2 | BSD-2-Clause | devDependency |
| 23 | vite | 8.0.10 | MIT | devDependency |
