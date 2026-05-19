# awslabs/apn_funding_wizard_mcp_server/consts.py
#
# Document path configuration for the APN Funding Wizard MCP Server.
# Place your organization's funding program documentation in the docs/ subdirectories.
# The server reads markdown files from these paths to provide program-specific guidance.

base_path = "../mcp_servers/src/"
getting_started_root_path = base_path+"apn-funding-wizard-mcp-server/awslabs/apn_funding_wizard_mcp_server/docs/get-started/"
build_root_path = base_path+"apn-funding-wizard-mcp-server/awslabs/apn_funding_wizard_mcp_server/docs/build/"
market_root_path = base_path+"apn-funding-wizard-mcp-server/awslabs/apn_funding_wizard_mcp_server/docs/market/"
sell_root_path = base_path+"apn-funding-wizard-mcp-server/awslabs/apn_funding_wizard_mcp_server/docs/sell/"

# Configure your funding program documentation paths below.
# Each key is a display name, each value is the file path.
# Place your .md files in the appropriate docs/ subdirectory.

GETTING_STARTED_DOCS = {
    # Example: "Introduction to Funding Benefits": getting_started_root_path + "introduction.md",
}

BUILD_DOCS = {
    # Example: "Innovation Sandbox Benefits": build_root_path + "innovation-sandbox.md",
}

MARKETING_DOCS = {
    # Example: "Marketing Development Funds": market_root_path + "mdf-benefits.md",
}

SELL_AND_GROW_DOCS = {
    # Example: "POC Full Benefits": sell_root_path + "poc-full-benefits.md",
    # Example: "MAP Full Benefits": sell_root_path + "map-full-benefits.md",
}
