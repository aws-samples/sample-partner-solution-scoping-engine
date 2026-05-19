# AWS Labs apn-funding-wizard MCP Server

An AWS Labs Model Context Protocol (MCP) server for apn-funding-wizard

## Instructions

Instructions for using this apn-funding-wizard MCP server. This can be used by clients to improve the LLM's understanding of available tools, resources, etc. It can be thought of like a 'hint' to the model. For example, this information MAY be added to the system prompt. Important to be clear, direct, and detailed.

## Provisioning Funding Program Documentation

This MCP server requires funding program documentation to provide guidance. The markdown files are not included in the repository and must be sourced from AWS Partner Central.

### Steps

1. **Download documents from AWS Partner Central**  
   Log in to [AWS Partner Central](https://partnercentral.awspartner.com) and download the relevant funding program guides (PDF/HTML) for the programs you want to support (e.g., POC, MAP, Innovation Sandbox, MDF).

2. **Convert documents to Markdown**  
   Convert the downloaded documents to `.md` format. You can use tools like `pandoc`, `markdownify`, or manually reformat. Ensure the content is clean and well-structured.

3. **Place files in the appropriate subdirectory**  
   - `awslabs/apn_funding_wizard_mcp_server/docs/get-started/` — Introductory / getting started funding docs
   - `awslabs/apn_funding_wizard_mcp_server/docs/build/` — Build-phase programs (e.g., Innovation Sandbox)
   - `awslabs/apn_funding_wizard_mcp_server/docs/market/` — Marketing programs (e.g., MDF)
   - `awslabs/apn_funding_wizard_mcp_server/docs/sell/` — Sell & grow programs (e.g., POC, MAP)

4. **Register files in `consts.py`**  
   Edit `awslabs/apn_funding_wizard_mcp_server/consts.py` and add entries to the appropriate dictionary. For example:
   ```python
   SELL_AND_GROW_DOCS = {
       "POC Full Benefits": sell_root_path + "poc-full-benefits.md",
       "MAP Full Benefits": sell_root_path + "map-full-benefits.md",
   }
   ```

The server reads these markdown files at runtime to provide program-specific funding guidance.

## TODO (REMOVE AFTER COMPLETING)

* [ ] Optionally add an ["RFC issue"](https://github.com/awslabs/mcp/issues) for the community to review
* [ ] Generate a `uv.lock` file with `uv sync` -> See [Getting Started](https://docs.astral.sh/uv/getting-started/)
* [ ] Remove the example tools in `./awslabs/apn_funding_wizard_mcp_server/server.py`
* [ ] Add your own tool(s) following the [DESIGN_GUIDELINES.md](https://github.com/awslabs/mcp/blob/main/DESIGN_GUIDELINES.md)
* [ ] Keep test coverage at or above the `main` branch - NOTE: GitHub Actions run this command for CodeCov metrics `uv run --frozen pytest --cov --cov-branch --cov-report=term-missing`
* [ ] Document the MCP Server in this "README.md"
* [ ] Add a section for this apn-funding-wizard MCP Server at the top level of this repository "../../README.md"
* [ ] Create the "../../doc/servers/apn-funding-wizard-mcp-server.md" file with these contents:

    ```markdown
    ---
    title: apn-funding-wizard MCP Server
    ---

    {% include "../../src/apn-funding-wizard-mcp-server/README.md" %}
    ```
  
* [ ] Reference within the "../../doc/index.md" like this:

    ```markdown
    ### apn-funding-wizard MCP Server
    
    An AWS Labs Model Context Protocol (MCP) server for apn-funding-wizard
    
    **Features:**
    
    - Feature one
    - Feature two
    - ...

    Instructions for using this apn-funding-wizard MCP server. This can be used by clients to improve the LLM's understanding of available tools, resources, etc. It can be thought of like a 'hint' to the model. For example, this information MAY be added to the system prompt. Important to be clear, direct, and detailed.
    
    [Learn more about the apn-funding-wizard MCP Server](servers/apn-funding-wizard-mcp-server.md)
    ```

* [ ] Submit a PR and pass all the checks
