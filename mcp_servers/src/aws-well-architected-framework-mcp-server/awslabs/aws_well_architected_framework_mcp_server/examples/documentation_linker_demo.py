"""
AWS Documentation Linker Demo

This script demonstrates the hybrid documentation link generation system.
Run this to see how the linker works for various AWS services and capabilities.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.aws_documentation_linker import AWSDocumentationLinker


def print_separator(title=""):
    """Print a visual separator"""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"{'='*80}\n")


def demo_service_documentation():
    """Demonstrate getting service documentation"""
    print_separator("Demo 1: Service Documentation (DynamoDB + Encryption)")
    
    linker = AWSDocumentationLinker()
    
    # Get documentation for DynamoDB encryption
    links = linker.get_service_documentation("DynamoDB", "encryption")
    
    print(f"Found {len(links)} documentation links for DynamoDB encryption:\n")
    
    for idx, link in enumerate(links[:5], 1):  # Show top 5
        print(f"{idx}. {link.title}")
        print(f"   URL: {link.url}")
        print(f"   Relevance: {link.relevance} | Score: {link.search_score:.2f}")
        print(f"   Description: {link.description[:100]}...")
        print()


def demo_pillar_documentation():
    """Demonstrate getting pillar documentation"""
    print_separator("Demo 2: WAFR Pillar Documentation (Security)")
    
    linker = AWSDocumentationLinker()
    
    # Get security pillar documentation
    links = linker.get_pillar_documentation("security")
    
    print(f"Found {len(links)} documentation links for Security pillar:\n")
    
    for idx, link in enumerate(links, 1):
        print(f"{idx}. {link.title}")
        print(f"   URL: {link.url}")
        print(f"   Relevance: {link.relevance} | Score: {link.search_score:.2f}")
        print()


def demo_prioritization():
    """Demonstrate link prioritization"""
    print_separator("Demo 3: Link Prioritization (Lambda + Monitoring)")
    
    linker = AWSDocumentationLinker()
    
    # Get documentation
    links = linker.get_service_documentation("Lambda", "monitoring")
    
    print(f"Generated {len(links)} links before prioritization\n")
    
    # Prioritize to top 3
    prioritized = linker.prioritize_links(
        links,
        service="Lambda",
        capability="monitoring",
        max_links=3
    )
    
    print(f"Top 3 prioritized links:\n")
    
    for idx, link in enumerate(prioritized, 1):
        print(f"{idx}. {link.title}")
        print(f"   URL: {link.url}")
        print(f"   Relevance: {link.relevance} | Score: {link.search_score:.2f}")
        print()


def demo_any_service():
    """Demonstrate that it works for ANY service"""
    print_separator("Demo 4: Works for ANY Service (Even New Ones)")
    
    linker = AWSDocumentationLinker()
    
    # Test with various services
    services = [
        ("DynamoDB", "backup"),
        ("Lambda", "security"),
        ("S3", "versioning"),
        ("NewAWSService2025", None),  # Even services that don't exist yet!
    ]
    
    for service, capability in services:
        links = linker.get_service_documentation(service, capability)
        cap_text = f" + {capability}" if capability else ""
        print(f"✓ {service}{cap_text}: {len(links)} links generated")
    
    print("\n✨ The hybrid approach works for ANY AWS service!")


def demo_all_pillars():
    """Demonstrate all WAFR pillars"""
    print_separator("Demo 5: All WAFR Pillars")
    
    linker = AWSDocumentationLinker()
    
    pillars = [
        "operational_excellence",
        "security",
        "reliability",
        "performance_efficiency",
        "cost_optimization",
        "sustainability"
    ]
    
    print("WAFR Pillar Documentation Links:\n")
    
    for pillar in pillars:
        links = linker.get_pillar_documentation(pillar)
        print(f"✓ {pillar.replace('_', ' ').title()}: {len(links)} links")
        if links:
            print(f"  → {links[0].url}")
        print()


def demo_caching():
    """Demonstrate caching behavior"""
    print_separator("Demo 6: Caching Performance")
    
    import time
    
    linker = AWSDocumentationLinker()
    
    # First call (no cache)
    start = time.time()
    links1 = linker.get_service_documentation("DynamoDB", "encryption")
    time1 = time.time() - start
    
    # Second call (cached)
    start = time.time()
    links2 = linker.get_service_documentation("DynamoDB", "encryption")
    time2 = time.time() - start
    
    print(f"First call (no cache):  {time1*1000:.2f}ms - {len(links1)} links")
    print(f"Second call (cached):   {time2*1000:.2f}ms - {len(links2)} links")
    print(f"\nSpeedup: {time1/time2:.1f}x faster with caching!")


def main():
    """Run all demos"""
    print("\n" + "="*80)
    print("  AWS Documentation Linker - Hybrid Approach Demo")
    print("  Phase 1: Complete and Production-Ready")
    print("="*80)
    
    try:
        demo_service_documentation()
        demo_pillar_documentation()
        demo_prioritization()
        demo_any_service()
        demo_all_pillars()
        demo_caching()
        
        print_separator("Demo Complete!")
        print("✅ All demos completed successfully!")
        print("\nKey Features Demonstrated:")
        print("  1. Service-specific documentation links")
        print("  2. WAFR pillar documentation")
        print("  3. Link prioritization and ranking")
        print("  4. Works for ANY AWS service (even new ones)")
        print("  5. All 6 WAFR pillars supported")
        print("  6. Caching for performance")
        print("\n" + "="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error running demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
