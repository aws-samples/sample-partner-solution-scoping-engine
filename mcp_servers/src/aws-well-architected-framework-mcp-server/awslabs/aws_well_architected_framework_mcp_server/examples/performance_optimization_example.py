"""
Performance Optimization Example for WAFR Enterprise Scoring.

Demonstrates how to use the optimized scoring components for maximum performance.
"""

import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from awslabs.aws_well_architected_framework_mcp_server.core.capability_mapper import CapabilityMapper
from awslabs.aws_well_architected_framework_mcp_server.core.capability_scorer import CapabilityScorer
from awslabs.aws_well_architected_framework_mcp_server.core.pattern_adjuster import PatternAdjuster
from awslabs.aws_well_architected_framework_mcp_server.core.performance_optimizer import (
    PerformanceOptimizer,
    OptimizedScoringEngine
)
from awslabs.aws_well_architected_framework_mcp_server.core.caching_manager import CacheCoordinator


def example_basic_optimization():
    """
    Example 1: Basic optimization with parallel processing.
    """
    print("\n" + "="*80)
    print("Example 1: Basic Optimization with Parallel Processing")
    print("="*80)
    
    # Sample architecture
    detected_services = [
        'Lambda', 'API Gateway', 'DynamoDB', 'S3', 'CloudWatch',
        'KMS', 'IAM', 'Cognito', 'CloudFront', 'ElastiCache',
        'RDS', 'VPC', 'CloudTrail', 'X-Ray', 'SNS'
    ]
    
    service_configurations = {
        'Lambda': {'memory': 512, 'timeout': 30},
        'DynamoDB': {'encryption': 'enabled'},
        'S3': {'encryption': 'AES256'},
        'RDS': {'encrypted': True, 'multi_az': True}
    }
    
    # Initialize components
    mapper = CapabilityMapper()
    scorer = CapabilityScorer()
    optimizer = PerformanceOptimizer(max_workers=6)
    
    print(f"\n📊 Analyzing architecture with {len(detected_services)} services...")
    
    # Sequential capability detection (baseline)
    start_time = time.time()
    sequential_matrix = mapper.map_services_to_capabilities(
        detected_services,
        service_configurations
    )
    sequential_time = (time.time() - start_time) * 1000
    
    print(f"\n⏱️  Sequential capability detection: {sequential_time:.0f}ms")
    print(f"   Detected {sequential_matrix.get_capability_count()} capabilities")
    
    # Parallel capability detection (optimized)
    start_time = time.time()
    parallel_matrix = optimizer.parallel_capability_detection(
        mapper,
        detected_services,
        service_configurations
    )
    parallel_time = (time.time() - start_time) * 1000
    
    print(f"\n🚀 Parallel capability detection: {parallel_time:.0f}ms")
    print(f"   Detected {parallel_matrix.get_capability_count()} capabilities")
    print(f"   Speedup: {sequential_time / parallel_time:.2f}x")
    
    # Parallel score calculation
    start_time = time.time()
    pillar_scores = optimizer.parallel_score_calculation(
        scorer,
        parallel_matrix,
        len(detected_services)
    )
    score_time = (time.time() - start_time) * 1000
    
    print(f"\n📈 Parallel score calculation: {score_time:.0f}ms")
    for pillar, score in pillar_scores.items():
        print(f"   {pillar}: {score.final_score:.1f}%")
    
    # Get performance metrics
    metrics = optimizer.get_performance_metrics()
    print(f"\n📊 Performance Metrics:")
    print(f"   Capability detection avg: {metrics['capability_detection']['avg_ms']:.0f}ms")
    print(f"   Score calculation avg: {metrics['score_calculation']['avg_ms']:.0f}ms")


def example_optimized_scoring_engine():
    """
    Example 2: Using OptimizedScoringEngine (recommended for production).
    """
    print("\n" + "="*80)
    print("Example 2: OptimizedScoringEngine (Production-Ready)")
    print("="*80)
    
    # Sample architecture
    detected_services = [
        'Lambda', 'API Gateway', 'DynamoDB', 'S3', 'CloudWatch',
        'KMS', 'IAM', 'Cognito', 'CloudFront', 'ElastiCache',
        'RDS', 'VPC', 'CloudTrail', 'X-Ray', 'SNS',
        'SQS', 'EventBridge', 'Step Functions', 'ECS', 'ECR'
    ]
    
    service_configurations = {
        'Lambda': {'memory': 512, 'timeout': 30},
        'DynamoDB': {'encryption': 'enabled'},
        'S3': {'encryption': 'AES256', 'versioning': True},
        'RDS': {'encrypted': True, 'multi_az': True},
        'ElastiCache': {'engine': 'redis'},
        'ECS': {'launch_type': 'FARGATE'}
    }
    
    # Initialize components
    mapper = CapabilityMapper()
    scorer = CapabilityScorer()
    pattern_adjuster = PatternAdjuster()
    
    # Create optimized engine
    optimized_engine = OptimizedScoringEngine(
        mapper,
        scorer,
        pattern_adjuster,
        max_workers=6
    )
    
    print(f"\n📊 Analyzing architecture with {len(detected_services)} services...")
    
    # Calculate scores with all optimizations
    start_time = time.time()
    
    pillar_scores, capability_matrix, metrics = optimized_engine.calculate_optimized_scores(
        detected_services,
        service_configurations,
        []  # No patterns for this example
    )
    
    total_time = (time.time() - start_time) * 1000
    
    print(f"\n✅ Total assessment time: {total_time:.0f}ms (target: <5000ms)")
    print(f"\n📈 Pillar Scores:")
    for pillar, score in pillar_scores.items():
        print(f"   {pillar}: {score.final_score:.1f}% (confidence: {score.confidence_level:.2f})")
    
    avg_score = sum(s.final_score for s in pillar_scores.values()) / len(pillar_scores)
    print(f"\n   Overall Average: {avg_score:.1f}%")
    
    print(f"\n📊 Performance Breakdown:")
    print(f"   Total time: {metrics['total_assessment_time_ms']:.0f}ms")
    print(f"   Capabilities detected: {capability_matrix.get_capability_count()}")
    
    # Cache statistics
    cache_info = metrics['cache_info']
    cap_cache = cache_info['capability_definition_cache']
    total_requests = cap_cache['hits'] + cap_cache['misses']
    hit_rate = cap_cache['hits'] / total_requests if total_requests > 0 else 0
    
    print(f"\n💾 Cache Statistics:")
    print(f"   Cache hits: {cap_cache['hits']}")
    print(f"   Cache misses: {cap_cache['misses']}")
    print(f"   Hit rate: {hit_rate:.1%}")


def example_caching_benefits():
    """
    Example 3: Demonstrating caching benefits.
    """
    print("\n" + "="*80)
    print("Example 3: Caching Benefits")
    print("="*80)
    
    # Sample architecture
    detected_services = [
        'Lambda', 'API Gateway', 'DynamoDB', 'S3', 'CloudWatch',
        'KMS', 'IAM', 'Cognito', 'CloudFront', 'ElastiCache'
    ]
    
    service_configurations = {
        'Lambda': {'memory': 512, 'timeout': 30},
        'DynamoDB': {'encryption': 'enabled'},
        'S3': {'encryption': 'AES256'}
    }
    
    # Initialize components
    mapper = CapabilityMapper()
    scorer = CapabilityScorer()
    
    optimized_engine = OptimizedScoringEngine(
        mapper,
        scorer,
        max_workers=6
    )
    
    print(f"\n📊 Running assessment 3 times to demonstrate caching...")
    
    times = []
    
    for i in range(3):
        start_time = time.time()
        
        pillar_scores, capability_matrix, metrics = optimized_engine.calculate_optimized_scores(
            detected_services,
            service_configurations
        )
        
        elapsed_time = (time.time() - start_time) * 1000
        times.append(elapsed_time)
        
        cache_info = metrics['cache_info']['capability_definition_cache']
        total_requests = cache_info['hits'] + cache_info['misses']
        hit_rate = cache_info['hits'] / total_requests if total_requests > 0 else 0
        
        print(f"\n   Run {i+1}: {elapsed_time:.0f}ms (cache hit rate: {hit_rate:.1%})")
    
    print(f"\n📊 Performance Improvement:")
    print(f"   First run (cold cache): {times[0]:.0f}ms")
    print(f"   Second run (warm cache): {times[1]:.0f}ms")
    print(f"   Third run (warm cache): {times[2]:.0f}ms")
    
    if times[0] > 0:
        improvement = ((times[0] - times[1]) / times[0]) * 100
        print(f"   Improvement: {improvement:.1f}%")


def example_cache_management():
    """
    Example 4: Cache management and invalidation.
    """
    print("\n" + "="*80)
    print("Example 4: Cache Management")
    print("="*80)
    
    # Initialize cache coordinator
    config_dir = os.path.join(
        os.path.dirname(__file__),
        '..',
        'config'
    )
    
    cache_coordinator = CacheCoordinator(config_dir)
    
    print("\n💾 Cache Coordinator initialized")
    
    # Get configuration with caching
    print("\n📄 Loading configuration files...")
    
    config1 = cache_coordinator.config_cache.get_config('scoring/scoring_parameters.json')
    config2 = cache_coordinator.config_cache.get_config('scoring/scoring_parameters.json')  # Cached
    
    print("   First load: from file")
    print("   Second load: from cache")
    
    # Get cache metrics
    metrics = cache_coordinator.get_all_metrics()
    
    print(f"\n📊 Cache Metrics:")
    print(f"   Config cache hits: {metrics['config_cache']['hits']}")
    print(f"   Config cache misses: {metrics['config_cache']['misses']}")
    print(f"   Hit rate: {metrics['config_cache']['hit_rate']:.1%}")
    
    # Invalidate caches
    print("\n🔄 Invalidating all caches...")
    cache_coordinator.invalidate_all()
    
    print("   All caches cleared")
    
    # Load again (will be cache miss)
    config3 = cache_coordinator.config_cache.get_config('scoring/scoring_parameters.json')
    
    print("   Next load: from file (cache was cleared)")


def main():
    """
    Run all examples.
    """
    print("\n" + "="*80)
    print("WAFR Enterprise Scoring - Performance Optimization Examples")
    print("="*80)
    
    try:
        # Run examples
        example_basic_optimization()
        example_optimized_scoring_engine()
        example_caching_benefits()
        example_cache_management()
        
        print("\n" + "="*80)
        print("✅ All examples completed successfully!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
