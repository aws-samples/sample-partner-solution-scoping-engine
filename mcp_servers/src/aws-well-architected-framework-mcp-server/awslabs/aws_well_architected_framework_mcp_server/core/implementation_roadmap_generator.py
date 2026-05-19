"""
Implementation Roadmap Generator for WAFR Report Content Improvement.

This module generates actionable implementation roadmaps with phases, tasks,
time estimates, cost estimates, dependencies, and success criteria.
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from .logger import WAFRLogger


@dataclass
class RoadmapTask:
    """Represents a single task in the implementation roadmap."""

    id: str  # e.g., "1.1", "2.3"
    title: str
    description: str
    effort_hours: float
    implementation_cost: float  # One-time cost
    ongoing_cost: float  # Monthly AWS cost
    score_improvement: float
    dependencies: List[str] = field(default_factory=list)  # List of task IDs
    success_criteria: str = ""
    validation_command: str = ""
    priority: str = "medium"  # high, medium, low
    service: str = ""
    capability: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "effort_hours": self.effort_hours,
            "implementation_cost": self.implementation_cost,
            "ongoing_cost": self.ongoing_cost,
            "score_improvement": self.score_improvement,
            "dependencies": self.dependencies,
            "success_criteria": self.success_criteria,
            "validation_command": self.validation_command,
            "priority": self.priority,
            "service": self.service,
            "capability": self.capability
        }


@dataclass
class RoadmapPhase:
    """Represents a phase in the implementation roadmap."""

    phase_number: int
    phase_name: str
    description: str
    tasks: List[RoadmapTask] = field(default_factory=list)
    duration_weeks: float = 0.0
    total_effort_hours: float = 0.0
    implementation_cost_min: float = 0.0
    implementation_cost_max: float = 0.0
    ongoing_cost_min: float = 0.0
    ongoing_cost_max: float = 0.0
    score_improvement: float = 0.0
    success_criteria: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "phase_number": self.phase_number,
            "phase_name": self.phase_name,
            "description": self.description,
            "tasks": [task.to_dict() for task in self.tasks],
            "duration_weeks": self.duration_weeks,
            "total_effort_hours": self.total_effort_hours,
            "implementation_cost_range": f"${self.implementation_cost_min:,.0f}-${self.implementation_cost_max:,.0f}",
            "ongoing_cost_range": f"${self.ongoing_cost_min:,.0f}-${self.ongoing_cost_max:,.0f}",
            "score_improvement": self.score_improvement,
            "success_criteria": self.success_criteria
        }


class ImplementationRoadmapGenerator:
    """
    Generates actionable implementation roadmaps from WAFR recommendations.

    This generator organizes recommendations into phases with tasks, estimates
    time and cost, identifies dependencies, and provides success criteria.
    """

    # Task priority weights for ordering
    PRIORITY_WEIGHTS = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1
    }

    # Foundation tasks that must come first
    FOUNDATION_CAPABILITIES = {
        "vpc", "network", "iam", "kms", "logging", "monitoring"
    }

    # Task dependency rules
    DEPENDENCY_RULES = {
        "waf": ["vpc", "api_gateway"],
        "vpc_integration": ["vpc"],
        "encryption_kms": ["kms"],
        "backup": ["encryption"],
        "multi_az": ["vpc"],
        "auto_scaling": ["monitoring"],
        "alerting": ["monitoring", "logging"]
    }

    def __init__(self):
        """Initialize the ImplementationRoadmapGenerator."""
        self.logger = WAFRLogger(__name__)
        self.logger.info("ImplementationRoadmapGenerator initialized")

    def create_roadmap(
        self,
        recommendations: List[Dict[str, Any]],
        current_score: float,
        target_score: float = 90.0
    ) -> List[RoadmapPhase]:
        """
        Create implementation roadmap from recommendations.

        Args:
            recommendations: List of recommendation dictionaries
            current_score: Current WAFR score (0-100)
            target_score: Target WAFR score (0-100)

        Returns:
            List of RoadmapPhase objects organized by priority
        """
        self.logger.info(
            f"Creating roadmap: {len(recommendations)} recommendations, "
            f"current_score={current_score}, target_score={target_score}"
        )

        # Convert recommendations to tasks
        tasks = self._convert_recommendations_to_tasks(recommendations)

        # Identify dependencies
        tasks = self.identify_dependencies(tasks)

        # Group tasks into phases
        phases = self._group_tasks_into_phases(tasks)

        # Calculate phase metrics
        for phase in phases:
            phase.duration_weeks = self.estimate_phase_duration(phase.tasks)
            cost_data = self.calculate_phase_cost(phase.tasks)
            phase.implementation_cost_min = cost_data["implementation_min"]
            phase.implementation_cost_max = cost_data["implementation_max"]
            phase.ongoing_cost_min = cost_data["ongoing_min"]
            phase.ongoing_cost_max = cost_data["ongoing_max"]
            phase.total_effort_hours = sum(task.effort_hours for task in phase.tasks)
            phase.score_improvement = sum(task.score_improvement for task in phase.tasks)
            phase.success_criteria = self._generate_phase_success_criteria(phase)

        self.logger.info(f"Created roadmap with {len(phases)} phases")
        return phases

    def _convert_recommendations_to_tasks(
        self,
        recommendations: List[Dict[str, Any]]
    ) -> List[RoadmapTask]:
        """Convert recommendations to roadmap tasks."""
        tasks = []

        for idx, rec in enumerate(recommendations, 1):
            task = RoadmapTask(
                id=f"T{idx}",
                title=rec.get("title", "Untitled Task"),
                description=rec.get("description", ""),
                effort_hours=rec.get("effort_hours", 2.0),
                implementation_cost=rec.get("implementation_cost", 0.0),
                ongoing_cost=rec.get("ongoing_cost", 0.0),
                score_improvement=rec.get("score_improvement", 5.0),
                priority=rec.get("priority", "medium"),
                service=rec.get("service", ""),
                capability=rec.get("capability", ""),
                success_criteria=rec.get("success_criteria", ""),
                validation_command=rec.get("validation_command", "")
            )
            tasks.append(task)

        return tasks

    def _group_tasks_into_phases(
        self,
        tasks: List[RoadmapTask]
    ) -> List[RoadmapPhase]:
        """Group tasks into phases based on priority and dependencies."""
        # Phase 1: Foundation (critical infrastructure)
        foundation_tasks = [
            task for task in tasks
            if any(cap in task.capability.lower() for cap in self.FOUNDATION_CAPABILITIES)
            or task.priority == "critical"
        ]

        # Phase 2: Enhancement (security and reliability improvements)
        enhancement_tasks = [
            task for task in tasks
            if task not in foundation_tasks
            and task.priority in ["high", "medium"]
        ]

        # Phase 3: Optimization (cost and performance)
        optimization_tasks = [
            task for task in tasks
            if task not in foundation_tasks
            and task not in enhancement_tasks
        ]

        phases = []

        if foundation_tasks:
            # Assign task IDs within phase
            for idx, task in enumerate(foundation_tasks, 1):
                task.id = f"1.{idx}"

            phases.append(RoadmapPhase(
                phase_number=1,
                phase_name="Foundation",
                description="Establish core infrastructure and security controls",
                tasks=foundation_tasks
            ))

        if enhancement_tasks:
            phase_num = len(phases) + 1
            for idx, task in enumerate(enhancement_tasks, 1):
                task.id = f"{phase_num}.{idx}"

            phases.append(RoadmapPhase(
                phase_number=phase_num,
                phase_name="Enhancement",
                description="Improve security, reliability, and operational excellence",
                tasks=enhancement_tasks
            ))

        if optimization_tasks:
            phase_num = len(phases) + 1
            for idx, task in enumerate(optimization_tasks, 1):
                task.id = f"{phase_num}.{idx}"

            phases.append(RoadmapPhase(
                phase_number=phase_num,
                phase_name="Optimization",
                description="Optimize cost, performance, and sustainability",
                tasks=optimization_tasks
            ))

        return phases

    def estimate_phase_duration(
        self,
        tasks: List[RoadmapTask]
    ) -> float:
        """
        Estimate phase duration in weeks.

        Args:
            tasks: List of tasks in the phase

        Returns:
            Duration in weeks
        """
        if not tasks:
            return 0.0

        # Calculate total effort hours
        total_hours = sum(task.effort_hours for task in tasks)

        # Check for parallelizable tasks (no dependencies)
        dependency_graph = self._build_dependency_graph(tasks)
        max_depth = self._calculate_max_dependency_depth(dependency_graph)

        # Assume 40 hours per week, but account for dependencies
        # If tasks can be parallelized, duration is less than sequential
        if max_depth > 1:
            # Some tasks must be sequential
            sequential_factor = 0.7  # 70% can be parallelized
            effective_hours = total_hours * (1 - sequential_factor) + (total_hours * sequential_factor / 2)
        else:
            # All tasks can be done in parallel
            effective_hours = total_hours / 2

        weeks = effective_hours / 40.0

        # Round up to nearest 0.5 week
        weeks = round(weeks * 2) / 2

        # Minimum 1 week per phase
        return max(1.0, weeks)

    def identify_dependencies(
        self,
        tasks: List[RoadmapTask]
    ) -> List[RoadmapTask]:
        """
        Identify dependencies between tasks.

        Args:
            tasks: List of tasks to analyze

        Returns:
            Tasks with dependency information populated
        """
        self.logger.info(f"Identifying dependencies for {len(tasks)} tasks")

        # Build capability to task mapping
        capability_tasks = {}
        for task in tasks:
            cap = task.capability.lower().replace(" ", "_")
            if cap:
                capability_tasks[cap] = task.id

        # Apply dependency rules
        for task in tasks:
            cap = task.capability.lower().replace(" ", "_")

            # Check if this capability has dependencies
            for dep_cap, required_caps in self.DEPENDENCY_RULES.items():
                if dep_cap in cap:
                    for required_cap in required_caps:
                        # Find task that provides this capability
                        for other_task in tasks:
                            other_cap = other_task.capability.lower().replace(" ", "_")
                            if required_cap in other_cap and other_task.id != task.id:
                                if other_task.id not in task.dependencies:
                                    task.dependencies.append(other_task.id)
                                    self.logger.debug(
                                        f"Task {task.id} depends on {other_task.id}"
                                    )

        return tasks

    def _build_dependency_graph(
        self,
        tasks: List[RoadmapTask]
    ) -> Dict[str, List[str]]:
        """Build dependency graph from tasks."""
        graph = {}
        for task in tasks:
            graph[task.id] = task.dependencies
        return graph

    def _calculate_max_dependency_depth(
        self,
        graph: Dict[str, List[str]]
    ) -> int:
        """Calculate maximum dependency depth (longest chain)."""
        def get_depth(task_id: str, visited: Set[str]) -> int:
            if task_id in visited:
                return 0
            visited.add(task_id)

            deps = graph.get(task_id, [])
            if not deps:
                return 1

            max_dep_depth = max((get_depth(dep, visited.copy()) for dep in deps), default=0)
            return 1 + max_dep_depth

        if not graph:
            return 1

        return max(get_depth(task_id, set()) for task_id in graph.keys())

    def calculate_phase_cost(
        self,
        tasks: List[RoadmapTask]
    ) -> Dict[str, float]:
        """
        Calculate phase cost estimates.

        Args:
            tasks: List of tasks in the phase

        Returns:
            Dictionary with cost estimates
        """
        if not tasks:
            return {
                "implementation_min": 0.0,
                "implementation_max": 0.0,
                "ongoing_min": 0.0,
                "ongoing_max": 0.0
            }

        # Sum implementation costs (one-time)
        total_implementation = sum(task.implementation_cost for task in tasks)

        # Sum ongoing costs (monthly AWS costs)
        total_ongoing = sum(task.ongoing_cost for task in tasks)

        # Provide range (±20% for uncertainty)
        return {
            "implementation_min": total_implementation * 0.8,
            "implementation_max": total_implementation * 1.2,
            "ongoing_min": total_ongoing * 0.8,
            "ongoing_max": total_ongoing * 1.2
        }

    def calculate_score_improvement(
        self,
        tasks: List[RoadmapTask],
        current_score: float
    ) -> Dict[str, Any]:
        """
        Calculate expected score improvement from tasks.

        Args:
            tasks: List of tasks to implement
            current_score: Current WAFR score (0-100)

        Returns:
            Dictionary with score improvement data
        """
        total_improvement = sum(task.score_improvement for task in tasks)
        expected_score = min(100.0, current_score + total_improvement)

        # Determine risk level
        def get_risk_level(score: float) -> str:
            if score >= 80:
                return "Low"
            elif score >= 60:
                return "Medium"
            elif score >= 40:
                return "High"
            else:
                return "Critical"

        current_risk = get_risk_level(current_score)
        expected_risk = get_risk_level(expected_score)

        return {
            "current_score": current_score,
            "expected_score": expected_score,
            "total_improvement": total_improvement,
            "current_risk_level": current_risk,
            "expected_risk_level": expected_risk,
            "risk_level_change": current_risk != expected_risk
        }

    def _generate_phase_success_criteria(
        self,
        phase: RoadmapPhase
    ) -> List[str]:
        """Generate success criteria for a phase."""
        criteria = []

        # Add task-specific criteria
        for task in phase.tasks:
            if task.success_criteria:
                criteria.append(task.success_criteria)

        # Add phase-level criteria
        if phase.phase_name == "Foundation":
            criteria.append("All critical infrastructure components deployed")
            criteria.append("Security baseline established")
            criteria.append("Monitoring and logging operational")
        elif phase.phase_name == "Enhancement":
            criteria.append("All high-priority security controls implemented")
            criteria.append("Reliability improvements validated")
            criteria.append("Operational procedures documented")
        elif phase.phase_name == "Optimization":
            criteria.append("Cost optimization targets achieved")
            criteria.append("Performance benchmarks met")
            criteria.append("Sustainability goals documented")

        return criteria

    def generate_markdown_roadmap(
        self,
        phases: List[RoadmapPhase],
        current_score: float,
        target_score: float
    ) -> str:
        """
        Generate markdown-formatted roadmap.

        Args:
            phases: List of roadmap phases
            current_score: Current WAFR score
            target_score: Target WAFR score

        Returns:
            Markdown-formatted roadmap string
        """
        lines = []

        # Header
        lines.append("# Implementation Roadmap")
        lines.append("")
        lines.append(f"**Current Score:** {current_score:.1f}%")
        lines.append(f"**Target Score:** {target_score:.1f}%")
        lines.append("")

        # Summary
        total_weeks = sum(phase.duration_weeks for phase in phases)
        total_tasks = sum(len(phase.tasks) for phase in phases)
        lines.append("## Summary")
        lines.append(f"- **Total Duration:** {total_weeks:.1f} weeks")
        lines.append(f"- **Total Tasks:** {total_tasks}")
        lines.append(f"- **Phases:** {len(phases)}")
        lines.append("")

        # Phases
        for phase in phases:
            lines.append(f"## Phase {phase.phase_number}: {phase.phase_name}")
            lines.append(f"**Duration:** {phase.duration_weeks:.1f} weeks")
            lines.append(f"**Effort:** {phase.total_effort_hours:.0f} hours")
            lines.append(f"**Implementation Cost:** ${phase.implementation_cost_min:,.0f}-${phase.implementation_cost_max:,.0f}")
            lines.append(f"**Ongoing Cost:** ${phase.ongoing_cost_min:,.0f}-${phase.ongoing_cost_max:,.0f}/month")
            lines.append(f"**Score Improvement:** +{phase.score_improvement:.1f} points")
            lines.append("")
            lines.append(f"_{phase.description}_")
            lines.append("")

            # Tasks
            lines.append("### Tasks")
            for task in phase.tasks:
                deps = f" (depends on: {', '.join(task.dependencies)})" if task.dependencies else ""
                lines.append(f"- [ ] **{task.id}** {task.title}{deps}")
                lines.append(f"  - Effort: {task.effort_hours:.1f} hours")
                lines.append(f"  - Score Impact: +{task.score_improvement:.1f}")
                if task.success_criteria:
                    lines.append(f"  - Success: {task.success_criteria}")
                lines.append("")

            # Success Criteria
            if phase.success_criteria:
                lines.append("### Success Criteria")
                for criterion in phase.success_criteria:
                    lines.append(f"- {criterion}")
                lines.append("")

        return "\n".join(lines)
