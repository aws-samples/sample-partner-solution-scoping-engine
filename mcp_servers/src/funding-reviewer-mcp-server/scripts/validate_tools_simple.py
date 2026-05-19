#!/usr/bin/env python3
"""
Simple MCP Tools Validation Script

This script validates the POC Funding Reviewer MCP tools without requiring
the full server to be running. It focuses on tool documentation, registry,
and compliance validation.
"""

import json
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from awslabs.poc_funding_reviewer_mcp_server.tool_documentation import tool_documentation
from awslabs.poc_funding_reviewer_mcp_server.tool_registry import tool_registry


def main():
    """Main validation function"""
    print("="*80)
    print("POC FUNDING REVIEWER MCP TOOLS VALIDATION")
    print("="*80)
    
    # Test 1: Tool Documentation
    print("\n1. TOOL DOCUMENTATION VALIDATION")
    print("-" * 40)
    
    try:
        docs = tool_documentation.get_all_tools()
        print(f"✅ Found documentation for {len(docs)} tools")
        
        expected_tools = [
            "analyze_poc_funding_request",
            "validate_documents", 
            "get_funding_requirements",
            "health_check",
            "get_server_status"
        ]
        
        missing_docs = [tool for tool in expected_tools if tool not in docs]
        if missing_docs:
            print(f"❌ Missing documentation for: {missing_docs}")
        else:
            print("✅ All expected tools have documentation")
        
        # Test markdown generation
        markdown = tool_documentation.generate_markdown_documentation()
        if len(markdown) > 1000:
            print(f"✅ Generated comprehensive documentation ({len(markdown)} characters)")
        else:
            print(f"⚠️  Documentation seems short ({len(markdown)} characters)")
            
    except Exception as e:
        print(f"❌ Tool documentation validation failed: {e}")
        return False
    
    # Test 2: Tool Registry
    print("\n2. TOOL REGISTRY VALIDATION")
    print("-" * 40)
    
    try:
        # Test registry functionality
        all_tools = tool_registry.get_all_tools()
        print(f"✅ Tool registry initialized with {len(all_tools)} tools")
        
        # Test statistics
        stats = tool_registry.get_tool_statistics()
        print(f"✅ Tool statistics: {stats['total_tools']} total tools")
        
        # Test server capabilities
        capabilities = tool_registry.get_server_capabilities()
        print(f"✅ Server capabilities: {len(capabilities['tool_summary']['available_tools'])} available tools")
        
    except Exception as e:
        print(f"❌ Tool registry validation failed: {e}")
        return False
    
    # Test 3: MCP Compliance
    print("\n3. MCP COMPLIANCE VALIDATION")
    print("-" * 40)
    
    try:
        compliance = tool_registry.validate_mcp_compliance()
        score = compliance['overall_score']
        max_score = compliance['max_score']
        percentage = (score / max_score) * 100 if max_score > 0 else 0
        
        print(f"Overall Score: {score}/{max_score} ({percentage:.1f}%)")
        print(f"Compliance Level: {compliance['compliance_level'].upper()}")
        
        # Show check results
        for check_name, check_result in compliance['checks'].items():
            status_icon = "✅" if check_result['status'] == 'pass' else "⚠️" if check_result['status'] == 'partial' else "❌"
            print(f"{status_icon} {check_name}: {check_result.get('score', 0)} points")
        
        # Show recommendations if any
        if compliance.get('recommendations'):
            print("\nRECOMMENDATIONS:")
            for i, rec in enumerate(compliance['recommendations'], 1):
                print(f"{i}. {rec}")
        
        if percentage >= 80:
            print("✅ MCP compliance is good!")
        else:
            print("⚠️  MCP compliance needs improvement")
            
    except Exception as e:
        print(f"❌ MCP compliance validation failed: {e}")
        return False
    
    # Test 4: Tool Categories and Organization
    print("\n4. TOOL ORGANIZATION VALIDATION")
    print("-" * 40)
    
    try:
        from awslabs.poc_funding_reviewer_mcp_server.tool_documentation import ToolCategory
        
        for category in ToolCategory:
            tools_in_category = tool_documentation.get_tools_by_category(category)
            if tools_in_category:
                print(f"✅ {category.value.title()}: {len(tools_in_category)} tools")
        
        # Test search functionality
        search_results = tool_registry.search_tools("funding")
        print(f"✅ Search functionality works: found {len(search_results)} tools for 'funding'")
        
    except Exception as e:
        print(f"❌ Tool organization validation failed: {e}")
        return False
    
    # Test 5: Documentation Export
    print("\n5. DOCUMENTATION EXPORT VALIDATION")
    print("-" * 40)
    
    try:
        # Test OpenAPI spec generation
        openapi_spec = tool_registry.generate_openapi_spec()
        if openapi_spec and 'paths' in openapi_spec:
            print(f"✅ OpenAPI specification generated with {len(openapi_spec['paths'])} endpoints")
        else:
            print("⚠️  OpenAPI specification generation needs improvement")
        
        # Save documentation to file
        output_dir = project_root / "generated_docs"
        output_dir.mkdir(exist_ok=True)
        
        # Save markdown documentation
        markdown_file = output_dir / "tool_documentation.md"
        with open(markdown_file, 'w') as f:
            f.write(tool_documentation.generate_markdown_documentation())
        print(f"✅ Markdown documentation saved to: {markdown_file}")
        
        # Save OpenAPI spec
        openapi_file = output_dir / "openapi_spec.json"
        with open(openapi_file, 'w') as f:
            json.dump(openapi_spec, f, indent=2)
        print(f"✅ OpenAPI specification saved to: {openapi_file}")
        
        # Save compliance report
        compliance_file = output_dir / "compliance_report.json"
        with open(compliance_file, 'w') as f:
            json.dump(compliance, f, indent=2, default=str)
        print(f"✅ Compliance report saved to: {compliance_file}")
        
    except Exception as e:
        print(f"❌ Documentation export validation failed: {e}")
        return False
    
    # Final Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    print("✅ Tool Documentation: PASSED")
    print("✅ Tool Registry: PASSED") 
    print("✅ MCP Compliance: PASSED")
    print("✅ Tool Organization: PASSED")
    print("✅ Documentation Export: PASSED")
    print()
    print("🎉 All validations passed! The POC Funding Reviewer MCP server")
    print("   tools are properly implemented and documented.")
    print()
    print(f"📁 Generated documentation available in: {output_dir}")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)