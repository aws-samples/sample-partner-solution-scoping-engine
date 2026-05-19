"""WAFR Workflow Engine with Quality Requirements"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class WAFRStage(Enum):
    """WAFR assessment stages."""
    INITIAL = "initial"
    GATHERING_INFO = "gathering_info"
    SOLUTION_PROPOSED = "solution_proposed"
    SOLUTION_FINALIZED = "solution_finalized"


class QualityEnhancedWorkflowEngine:
    """Enforces mandatory 4-step WAFR workflow with quality requirements."""
    
    def __init__(self, analysis_engine, wafr_client, question_framework, report_generator):
        self.analysis_engine = analysis_engine
        self.wafr_client = wafr_client
        self.question_framework = question_framework
        self.report_generator = report_generator
        self.sessions = {}  # chat_id -> session state
        
    def get_session_state(self, chat_id: str) -> Dict[str, Any]:
        """Get or create session state."""
        if chat_id not in self.sessions:
            self.sessions[chat_id] = {
                "stage": WAFRStage.INITIAL,
                "correlation_id": str(uuid.uuid4()),
                "document_analysis": None,
                "pillar_assessments": {},
                "comprehensive_assessment": None,
                "report_data": None,
                "quality_metrics": {},
                "created_at": datetime.now().isoformat()
            }
        return self.sessions[chat_id]
    
    def transition_stage(self, chat_id: str, new_stage: WAFRStage) -> bool:
        """Transition to new stage with validation."""
        session = self.get_session_state(chat_id)
        current_stage = session["stage"]
        
        # Validate stage transitions
        valid_transitions = {
            WAFRStage.INITIAL: [WAFRStage.GATHERING_INFO],
            WAFRStage.GATHERING_INFO: [WAFRStage.SOLUTION_PROPOSED],
            WAFRStage.SOLUTION_PROPOSED: [WAFRStage.SOLUTION_FINALIZED],
            WAFRStage.SOLUTION_FINALIZED: []  # Terminal stage
        }
        
        if new_stage not in valid_transitions.get(current_stage, []):
            logger.warning(f"Invalid stage transition: {current_stage.value} → {new_stage.value}")
            return False
        
        session["stage"] = new_stage
        logger.info(f"Stage transition: {current_stage.value} → {new_stage.value}")
        return True
    
    async def execute_mandatory_workflow(
        self,
        chat_id: str,
        document_urls: List[str],
        document_filenames: List[str]
    ) -> Dict[str, Any]:
        """Execute the mandatory 4-step WAFR workflow with quality enforcement."""
        
        session = self.get_session_state(chat_id)
        correlation_id = session["correlation_id"]
        
        logger.info(f"🚀 Starting quality-enhanced WAFR workflow - Chat: {chat_id}, Correlation: {correlation_id}")
        
        try:
            # STEP 1: Document Analysis with Quality Requirements
            step1_result = await self._step1_quality_document_analysis(chat_id, document_urls, document_filenames)
            if not step1_result["success"]:
                return step1_result
            
            # STEP 2: Quality-Enhanced Pillar Assessments
            step2_result = await self._step2_quality_pillar_assessments(chat_id)
            if not step2_result["success"]:
                return step2_result
            
            # STEP 3: Quality-Validated Comprehensive Assessment
            step3_result = await self._step3_quality_comprehensive_assessment(chat_id)
            if not step3_result["success"]:
                return step3_result
            
            # STEP 4: Quality Professional Report
            step4_result = await self._step4_quality_professional_report(chat_id)
            if not step4_result["success"]:
                return step4_result
            
            # Calculate overall quality metrics
            overall_quality = self._calculate_overall_quality(session)
            
            # Workflow completed successfully
            return {
                "success": True,
                "workflow_status": "completed",
                "chat_id": chat_id,
                "correlation_id": correlation_id,
                "final_stage": WAFRStage.SOLUTION_FINALIZED.value,
                "quality_metrics": overall_quality,
                "results": {
                    "document_analysis": step1_result["data"],
                    "pillar_assessments": step2_result["data"],
                    "comprehensive_assessment": step3_result["data"],
                    "professional_report": step4_result["data"]
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Quality-enhanced WAFR workflow failed: {e}")
            return {
                "success": False,
                "workflow_status": "failed",
                "error": str(e),
                "chat_id": chat_id,
                "correlation_id": correlation_id,
                "current_stage": session["stage"].value
            }
    
    async def _step1_quality_document_analysis(self, chat_id: str, document_urls: List[str], document_filenames: List[str]) -> Dict[str, Any]:
        """STEP 1: Quality-enhanced document analysis."""
        
        logger.info(f"📄 STEP 1: Quality-Enhanced Document Analysis - {len(document_urls)} documents")
        session = self.get_session_state(chat_id)
        
        try:
            # Transition: INITIAL → GATHERING_INFO
            if not self.transition_stage(chat_id, WAFRStage.GATHERING_INFO):
                return {"success": False, "error": "Invalid stage transition for document analysis"}
            
            # Infer document types from filenames
            document_types = []
            for filename in document_filenames:
                if filename.lower().endswith('.pdf'):
                    document_types.append('pdf')
                elif filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    document_types.append('png')
                elif filename.lower().endswith('.txt'):
                    document_types.append('txt')
                else:
                    document_types.append('pdf')  # default
            
            # Analyze documents with quality requirements
            analysis_result = await self.analysis_engine.analyze_documents(document_urls, document_types)
            
            # Quality validation for document analysis
            quality_metrics = self._validate_document_analysis_quality(analysis_result)
            
            # Enhanced result with quality metrics
            enhanced_result = {
                **analysis_result,
                "quality_metrics": quality_metrics,
                "quality_score": quality_metrics.get("overall_score", 0),
                "meets_quality_requirements": quality_metrics.get("meets_requirements", False)
            }
            
            # Store in session
            session["document_analysis"] = enhanced_result
            session["quality_metrics"]["document_analysis"] = quality_metrics
            
            logger.info(f"✅ STEP 1 completed: Quality score {quality_metrics.get('overall_score', 0):.2f}")
            
            return {
                "success": True,
                "step": 1,
                "stage": WAFRStage.GATHERING_INFO.value,
                "data": enhanced_result
            }
            
        except Exception as e:
            logger.error(f"❌ STEP 1 failed: {e}")
            return {"success": False, "step": 1, "error": str(e)}
    
    async def _step2_quality_pillar_assessments(self, chat_id: str) -> Dict[str, Any]:
        """STEP 2: Quality-enhanced pillar assessments."""
        
        logger.info("🏛️ STEP 2: Quality-Enhanced Pillar Assessments")
        session = self.get_session_state(chat_id)
        
        try:
            # Transition: GATHERING_INFO → SOLUTION_PROPOSED
            if not self.transition_stage(chat_id, WAFRStage.SOLUTION_PROPOSED):
                return {"success": False, "error": "Invalid stage transition for pillar assessment"}
            
            pillars = [
                "operational_excellence",
                "security", 
                "reliability",
                "performance_efficiency",
                "cost_optimization",
                "sustainability"
            ]
            
            architecture_data = session.get("document_analysis", {})
            pillar_results = {}
            pillar_quality_metrics = {}
            
            # Assess each pillar with quality requirements
            for pillar in pillars:
                logger.info(f"🔍 Quality-assessing {pillar} pillar")
                
                try:
                    # Get pillar questions
                    questions = self.question_framework.get_pillar_questions(pillar)
                    
                    # Perform enhanced capability-based assessment
                    from .server import assess_pillar_compliance
                    assessment = await assess_pillar_compliance(pillar, architecture_data)
                    
                    # Quality validation for pillar assessment
                    quality_metrics = self._validate_pillar_assessment_quality(assessment, architecture_data)
                    
                    pillar_results[pillar] = {
                        "pillar": pillar,
                        "score": assessment.get("score", 0),
                        "risk_level": assessment.get("risk_level", "medium"),
                        "recommendations": assessment.get("recommendations", []),
                        "findings": assessment.get("findings", []),
                        "quality_metrics": quality_metrics,
                        "architecture_specific": quality_metrics.get("architecture_specific", False),
                        "business_context_considered": quality_metrics.get("business_context", False),
                        "concrete_steps_provided": quality_metrics.get("concrete_steps", False),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    pillar_quality_metrics[pillar] = quality_metrics
                    
                    logger.info(f"✅ {pillar} assessment completed - Score: {assessment.get('score', 0)}, Quality: {quality_metrics.get('overall_score', 0):.2f}")
                    
                except Exception as pillar_error:
                    logger.error(f"❌ {pillar} assessment failed: {pillar_error}")
                    pillar_results[pillar] = {
                        "pillar": pillar,
                        "error": str(pillar_error),
                        "score": 0,
                        "risk_level": "high",
                        "quality_metrics": {"overall_score": 0, "meets_requirements": False}
                    }
            
            # Store in session
            session["pillar_assessments"] = pillar_results
            session["quality_metrics"]["pillar_assessments"] = pillar_quality_metrics
            
            logger.info(f"✅ STEP 2 completed: All 6 pillars assessed with quality validation")
            
            return {
                "success": True,
                "step": 2,
                "stage": WAFRStage.SOLUTION_PROPOSED.value,
                "data": pillar_results
            }
            
        except Exception as e:
            logger.error(f"❌ STEP 2 failed: {e}")
            return {"success": False, "step": 2, "error": str(e)}
    
    async def _step3_quality_comprehensive_assessment(self, chat_id: str) -> Dict[str, Any]:
        """STEP 3: Quality-validated comprehensive assessment."""
        
        logger.info("📊 STEP 3: Quality-Validated Comprehensive Assessment")
        session = self.get_session_state(chat_id)
        
        try:
            pillar_assessments = session.get("pillar_assessments", {})
            architecture_data = session.get("document_analysis", {})
            
            # Calculate overall scores with quality weighting
            valid_scores = []
            quality_weighted_scores = []
            
            for pillar_data in pillar_assessments.values():
                if pillar_data.get("score") is not None:
                    score = pillar_data["score"]
                    converted_score = score * 10 if score <= 10 else score
                    valid_scores.append(converted_score)
                    
                    # Weight score by quality metrics
                    quality_score = pillar_data.get("quality_metrics", {}).get("overall_score", 0.5)
                    weighted_score = converted_score * (0.5 + 0.5 * quality_score)  # 50% base + 50% quality weighted
                    quality_weighted_scores.append(weighted_score)
            
            overall_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0
            quality_weighted_overall = sum(quality_weighted_scores) / len(quality_weighted_scores) if quality_weighted_scores else 0
            
            overall_risk_level = "high" if quality_weighted_overall < 60 else "medium" if quality_weighted_overall < 80 else "low"
            
            # Generate high priority actions with quality focus
            high_priority_actions = []
            for pillar_data in pillar_assessments.values():
                if pillar_data.get("recommendations") and pillar_data.get("quality_metrics", {}).get("meets_requirements", False):
                    high_priority_actions.extend(pillar_data["recommendations"][:2])
            
            # Quality assessment of comprehensive results
            comprehensive_quality = self._validate_comprehensive_assessment_quality(pillar_assessments, architecture_data)
            
            comprehensive_result = {
                "assessment_id": f"wafr-{chat_id}-{datetime.now().strftime('%Y%m%d')}",
                "chat_id": chat_id,
                "overall_score": overall_score,
                "quality_weighted_score": quality_weighted_overall,
                "overall_risk_level": overall_risk_level,
                "pillar_assessments": pillar_assessments,
                "document_analysis": architecture_data,
                "high_priority_actions": high_priority_actions[:8],
                "quality_metrics": comprehensive_quality,
                "meets_quality_standards": comprehensive_quality.get("meets_requirements", False),
                "timestamp": datetime.now().isoformat()
            }
            
            # Store in session
            session["comprehensive_assessment"] = comprehensive_result
            session["quality_metrics"]["comprehensive_assessment"] = comprehensive_quality
            
            logger.info(f"✅ STEP 3 completed: Overall score {overall_score:.1f}, Quality-weighted {quality_weighted_overall:.1f}")
            
            return {
                "success": True,
                "step": 3,
                "stage": WAFRStage.SOLUTION_PROPOSED.value,
                "data": comprehensive_result
            }
            
        except Exception as e:
            logger.error(f"❌ STEP 3 failed: {e}")
            return {"success": False, "step": 3, "error": str(e)}
    
    async def _step4_quality_professional_report(self, chat_id: str) -> Dict[str, Any]:
        """STEP 4: Quality professional report generation."""
        
        logger.info("📋 STEP 4: Quality Professional Report Generation")
        session = self.get_session_state(chat_id)
        
        try:
            # Transition: SOLUTION_PROPOSED → SOLUTION_FINALIZED
            if not self.transition_stage(chat_id, WAFRStage.SOLUTION_FINALIZED):
                return {"success": False, "error": "Invalid stage transition for report generation"}
            
            assessment_data = session.get("comprehensive_assessment", {})
            
            if not assessment_data:
                return {"success": False, "error": "No assessment data available for report generation"}
            
            # Generate quality-enhanced report
            report_content = await self.report_generator.generate_report(assessment_data, ["all"])
            
            # Quality validation of report
            report_quality = self._validate_report_quality(report_content, assessment_data)
            
            # Create report metadata with quality metrics
            report_result = {
                "report_generated": True,
                "chat_id": chat_id,
                "report_size": len(report_content) if report_content else 0,
                "generation_timestamp": datetime.now().isoformat(),
                "assessment_id": assessment_data.get("assessment_id"),
                "overall_score": assessment_data.get("overall_score", 0),
                "quality_weighted_score": assessment_data.get("quality_weighted_score", 0),
                "quality_metrics": report_quality,
                "meets_quality_standards": report_quality.get("meets_requirements", False)
            }
            
            # Store in session
            session["report_data"] = report_result
            session["quality_metrics"]["report"] = report_quality
            
            logger.info(f"✅ STEP 4 completed: Quality report generated ({len(report_content)} bytes)")
            
            return {
                "success": True,
                "step": 4,
                "stage": WAFRStage.SOLUTION_FINALIZED.value,
                "data": report_result
            }
            
        except Exception as e:
            logger.error(f"❌ STEP 4 failed: {e}")
            return {"success": False, "step": 4, "error": str(e)}
    
    def _validate_document_analysis_quality(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate document analysis quality."""
        
        services_count = len(analysis_result.get("identified_services", []))
        patterns_count = len(analysis_result.get("architecture_patterns", []))
        
        quality_score = min(1.0, (services_count / 5 + patterns_count / 3) / 2)
        
        return {
            "overall_score": quality_score,
            "services_identified": services_count,
            "patterns_identified": patterns_count,
            "meets_requirements": quality_score >= 0.6
        }
    
    def _validate_pillar_assessment_quality(self, assessment: Dict[str, Any], architecture_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pillar assessment quality."""
        
        recommendations_count = len(assessment.get("recommendations", []))
        findings_count = len(assessment.get("findings", []))
        has_architecture_context = len(architecture_data.get("identified_services", [])) > 0
        
        quality_score = min(1.0, (recommendations_count / 3 + findings_count / 3 + (1 if has_architecture_context else 0)) / 3)
        
        return {
            "overall_score": quality_score,
            "recommendations_count": recommendations_count,
            "findings_count": findings_count,
            "architecture_specific": has_architecture_context,
            "business_context": recommendations_count > 0,
            "concrete_steps": findings_count > 0,
            "meets_requirements": quality_score >= 0.6
        }
    
    def _validate_comprehensive_assessment_quality(self, pillar_assessments: Dict[str, Any], architecture_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate comprehensive assessment quality."""
        
        completed_pillars = len([p for p in pillar_assessments.values() if p.get("score", 0) > 0])
        quality_pillars = len([p for p in pillar_assessments.values() if p.get("quality_metrics", {}).get("meets_requirements", False)])
        
        quality_score = min(1.0, (completed_pillars / 6 + quality_pillars / 6) / 2)
        
        return {
            "overall_score": quality_score,
            "completed_pillars": completed_pillars,
            "quality_pillars": quality_pillars,
            "meets_requirements": quality_score >= 0.7
        }
    
    def _validate_report_quality(self, report_content: bytes, assessment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate report quality."""
        
        has_content = len(report_content) > 1000 if report_content else False
        has_assessment_data = bool(assessment_data.get("pillar_assessments"))
        meets_quality = assessment_data.get("meets_quality_standards", False)
        
        quality_score = (int(has_content) + int(has_assessment_data) + int(meets_quality)) / 3
        
        return {
            "overall_score": quality_score,
            "has_content": has_content,
            "has_assessment_data": has_assessment_data,
            "meets_quality_standards": meets_quality,
            "meets_requirements": quality_score >= 0.7
        }
    
    def _calculate_overall_quality(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall workflow quality metrics."""
        
        quality_metrics = session.get("quality_metrics", {})
        
        scores = []
        for step_metrics in quality_metrics.values():
            if isinstance(step_metrics, dict) and "overall_score" in step_metrics:
                scores.append(step_metrics["overall_score"])
        
        overall_score = sum(scores) / len(scores) if scores else 0
        
        return {
            "overall_quality_score": overall_score,
            "step_quality_scores": quality_metrics,
            "meets_quality_requirements": overall_score >= 0.7,
            "quality_grade": "A" if overall_score >= 0.9 else "B" if overall_score >= 0.7 else "C" if overall_score >= 0.5 else "D"
        }
