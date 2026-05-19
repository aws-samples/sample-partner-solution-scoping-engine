"""
Questions Assessed Counter for WAFR Report Quality Enhancement.

This module tracks how many official WAFR questions were evaluated during
pillar assessments, providing transparency about assessment thoroughness.
"""

from typing import Dict, Optional
from dataclasses import dataclass, field

from ..core.logger import WAFRLogger


@dataclass
class QuestionCoverageMetrics:
    """Metrics for question coverage in an assessment."""
    pillar: str
    questions_assessed: int
    total_questions_available: int
    coverage_percentage: float
    assessment_method: str = "hybrid"  # "api", "hybrid", "fallback"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "pillar": self.pillar,
            "questions_assessed": self.questions_assessed,
            "total_questions_available": self.total_questions_available,
            "coverage_percentage": round(self.coverage_percentage, 2),
            "assessment_method": self.assessment_method
        }


class QuestionsAssessedCounter:
    """
    Tracks the number of WAFR questions assessed per pillar.
    
    This component provides transparency about assessment thoroughness by
    counting how many official WAFR questions were evaluated and calculating
    coverage percentages.
    
    Example:
        counter = QuestionsAssessedCounter()
        
        # Increment when questions are assessed
        counter.increment_question_count("security", 5)
        counter.increment_question_count("security", 3)
        
        # Get total count
        count = counter.get_question_count("security")  # Returns: 8
        
        # Get coverage metrics
        metrics = counter.get_coverage_metrics("security", total_available=50)
        # Returns: QuestionCoverageMetrics with 16% coverage
    """
    
    # Estimated total questions per pillar (from AWS Well-Architected Framework)
    # These are approximate counts based on the official framework
    ESTIMATED_TOTAL_QUESTIONS = {
        "security": 50,
        "reliability": 45,
        "performance_efficiency": 40,
        "cost_optimization": 45,
        "operational_excellence": 40,
        "sustainability": 35
    }
    
    def __init__(self):
        """Initialize the questions assessed counter."""
        self.logger = WAFRLogger(__name__)
        self._pillar_questions: Dict[str, int] = {}
        self._assessment_methods: Dict[str, str] = {}
        self.logger.info("QuestionsAssessedCounter initialized")
    
    def increment_question_count(
        self,
        pillar: str,
        count: int = 1,
        assessment_method: Optional[str] = None
    ) -> None:
        """
        Increment the question count for a pillar.
        
        Args:
            pillar: WAFR pillar name
            count: Number of questions to add (default: 1)
            assessment_method: Method used for assessment ("api", "hybrid", "fallback")
        """
        if pillar not in self._pillar_questions:
            self._pillar_questions[pillar] = 0
        
        self._pillar_questions[pillar] += count
        
        if assessment_method:
            self._assessment_methods[pillar] = assessment_method
        
        self.logger.debug(
            f"Incremented question count for {pillar}: +{count} "
            f"(total: {self._pillar_questions[pillar]})"
        )
    
    def set_question_count(
        self,
        pillar: str,
        count: int,
        assessment_method: Optional[str] = None
    ) -> None:
        """
        Set the question count for a pillar directly.
        
        Args:
            pillar: WAFR pillar name
            count: Total number of questions assessed
            assessment_method: Method used for assessment
        """
        self._pillar_questions[pillar] = count
        
        if assessment_method:
            self._assessment_methods[pillar] = assessment_method
        
        self.logger.debug(f"Set question count for {pillar}: {count}")
    
    def get_question_count(self, pillar: str) -> int:
        """
        Get the number of questions assessed for a pillar.
        
        Args:
            pillar: WAFR pillar name
            
        Returns:
            Number of questions assessed (0 if pillar not found)
        """
        return self._pillar_questions.get(pillar, 0)
    
    def get_total_questions(self) -> int:
        """
        Get total questions assessed across all pillars.
        
        Returns:
            Total number of questions assessed
        """
        return sum(self._pillar_questions.values())
    
    def get_coverage_percentage(
        self,
        pillar: str,
        total_available: Optional[int] = None
    ) -> float:
        """
        Calculate percentage of available questions that were assessed.
        
        Args:
            pillar: WAFR pillar name
            total_available: Total questions available for this pillar
                           (uses estimated count if not provided)
            
        Returns:
            Coverage percentage (0-100)
        """
        questions_assessed = self.get_question_count(pillar)
        
        if total_available is None:
            total_available = self.ESTIMATED_TOTAL_QUESTIONS.get(pillar, 50)
        
        if total_available == 0:
            return 0.0
        
        coverage = (questions_assessed / total_available) * 100
        return min(100.0, coverage)  # Cap at 100%
    
    def get_coverage_metrics(
        self,
        pillar: str,
        total_available: Optional[int] = None
    ) -> QuestionCoverageMetrics:
        """
        Get comprehensive coverage metrics for a pillar.
        
        Args:
            pillar: WAFR pillar name
            total_available: Total questions available for this pillar
            
        Returns:
            QuestionCoverageMetrics object with detailed metrics
        """
        if total_available is None:
            total_available = self.ESTIMATED_TOTAL_QUESTIONS.get(pillar, 50)
        
        questions_assessed = self.get_question_count(pillar)
        coverage_percentage = self.get_coverage_percentage(pillar, total_available)
        assessment_method = self._assessment_methods.get(pillar, "unknown")
        
        return QuestionCoverageMetrics(
            pillar=pillar,
            questions_assessed=questions_assessed,
            total_questions_available=total_available,
            coverage_percentage=coverage_percentage,
            assessment_method=assessment_method
        )
    
    def get_all_coverage_metrics(self) -> Dict[str, QuestionCoverageMetrics]:
        """
        Get coverage metrics for all assessed pillars.
        
        Returns:
            Dictionary mapping pillar names to QuestionCoverageMetrics
        """
        metrics = {}
        
        for pillar in self._pillar_questions.keys():
            metrics[pillar] = self.get_coverage_metrics(pillar)
        
        return metrics
    
    def get_assessment_summary(self) -> Dict:
        """
        Get a summary of the assessment coverage.
        
        Returns:
            Dictionary with summary statistics
        """
        total_assessed = self.get_total_questions()
        total_available = sum(
            self.ESTIMATED_TOTAL_QUESTIONS.get(pillar, 50)
            for pillar in self._pillar_questions.keys()
        )
        
        overall_coverage = (
            (total_assessed / total_available * 100)
            if total_available > 0 else 0.0
        )
        
        # Calculate coverage levels
        high_coverage_pillars = []
        medium_coverage_pillars = []
        low_coverage_pillars = []
        
        for pillar in self._pillar_questions.keys():
            coverage = self.get_coverage_percentage(pillar)
            if coverage >= 70:
                high_coverage_pillars.append(pillar)
            elif coverage >= 40:
                medium_coverage_pillars.append(pillar)
            else:
                low_coverage_pillars.append(pillar)
        
        return {
            "total_questions_assessed": total_assessed,
            "total_questions_available": total_available,
            "overall_coverage_percentage": round(overall_coverage, 2),
            "pillars_assessed": len(self._pillar_questions),
            "coverage_levels": {
                "high_coverage": high_coverage_pillars,  # >= 70%
                "medium_coverage": medium_coverage_pillars,  # 40-69%
                "low_coverage": low_coverage_pillars  # < 40%
            },
            "assessment_methods": self._assessment_methods
        }
    
    def reset(self) -> None:
        """Reset all question counts."""
        self._pillar_questions.clear()
        self._assessment_methods.clear()
        self.logger.info("Question counts reset")
    
    def reset_pillar(self, pillar: str) -> None:
        """
        Reset question count for a specific pillar.
        
        Args:
            pillar: WAFR pillar name
        """
        if pillar in self._pillar_questions:
            del self._pillar_questions[pillar]
        if pillar in self._assessment_methods:
            del self._assessment_methods[pillar]
        
        self.logger.debug(f"Reset question count for {pillar}")
    
    def get_coverage_interpretation(self, coverage_percentage: float) -> str:
        """
        Get a human-readable interpretation of coverage percentage.
        
        Args:
            coverage_percentage: Coverage percentage (0-100)
            
        Returns:
            Interpretation string
        """
        if coverage_percentage >= 80:
            return "Excellent - Comprehensive assessment with high confidence"
        elif coverage_percentage >= 60:
            return "Good - Thorough assessment with solid coverage"
        elif coverage_percentage >= 40:
            return "Fair - Moderate assessment, consider additional questions"
        elif coverage_percentage >= 20:
            return "Limited - Basic assessment, significant gaps may exist"
        else:
            return "Minimal - Very limited assessment, results may not be comprehensive"
    
    def to_dict(self) -> Dict:
        """
        Convert counter state to dictionary for serialization.
        
        Returns:
            Dictionary with all counter data
        """
        return {
            "pillar_questions": self._pillar_questions.copy(),
            "assessment_methods": self._assessment_methods.copy(),
            "summary": self.get_assessment_summary()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'QuestionsAssessedCounter':
        """
        Create counter from dictionary data.
        
        Args:
            data: Dictionary with counter data
            
        Returns:
            QuestionsAssessedCounter instance
        """
        counter = cls()
        counter._pillar_questions = data.get("pillar_questions", {}).copy()
        counter._assessment_methods = data.get("assessment_methods", {}).copy()
        return counter
