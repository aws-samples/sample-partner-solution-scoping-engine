"""WAFR Workflow Engine - Mandatory 4-Step Assessment Process"""

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


class WAFRWorkflowEngine:
    """Enforces mandatory 4-step WAFR workflow."""
    
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
        """Execute the mandatory 4-step WAFR workflow."""
        
        session = self.get_session_state(chat_id)
        correlation_id = session["correlation_id"]
        
        logger.info(f"🚀 Starting mandatory WAFR workflow - Chat: {chat_id}, Correlation: {correlation_id}")
        
        try:
            # STEP 1: Document Analysis
            step1_result = await self._step1_document_analysis(chat_id, document_urls, document_filenames)
            if not step1_result["success"]:
                return step1_result
            
            # STEP 2: Individual Pillar Assessments (all 6 pillars)
            step2_result = await self._step2_pillar_assessments(chat_id)
            if not step2_result["success"]:
                return step2_result
            
            # STEP 3: Comprehensive Assessment
            step3_result = await self._step3_comprehensive_assessment(chat_id)
            if not step3_result["success"]:
                return step3_result
            
            # STEP 4: Professional Report
            step4_result = await self._step4_professional_report(chat_id)
            if not step4_result["success"]:
                return step4_result
            
            # Workflow completed successfully
            return {
                "success": True,
                "workflow_status": "completed",
                "chat_id": chat_id,
                "correlation_id": correlation_id,
                "final_stage": WAFRStage.SOLUTION_FINALIZED.value,
                "results": {
                    "document_analysis": step1_result["data"],
                    "pillar_assessments": step2_result["data"],
                    "comprehensive_assessment": step3_result["data"],
                    "professional_report": step4_result["data"]
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ WAFR workflow failed: {e}")
            return {
                "success": False,
                "workflow_status": "failed",
                "error": str(e),
                "chat_id": chat_id,
                "correlation_id": correlation_id,
                "current_stage": session["stage"].value
            }
    
    async def _step1_document_analysis(self, chat_id: str, document_urls: List[str], document_filenames: List[str]) -> Dict[str, Any]:
        """STEP 1: Document Analysis with stage transition."""
        
        logger.info(f"📄 STEP 1: Document Analysis - {len(document_urls)} documents")
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
            
            # Analyze documents
            analysis_result = await self.analysis_engine.analyze_documents(document_urls, document_types)
            
            # Store in session
            session["document_analysis"] = analysis_result
            
            logger.info(f"✅ STEP 1 completed: {len(analysis_result.get('identified_services', []))} services found")
            
            return {
                "success": True,
                "step": 1,
                "stage": WAFRStage.GATHERING_INFO.value,
                "data": analysis_result
            }
            
        except Exception as e:
            logger.error(f"❌ STEP 1 failed: {e}")
            return {"success": False, "step": 1, "error": str(e)}
    
    async def _step2_pillar_assessments(self, chat_id: str) -> Dict[str, Any]:
        """STEP 2: Individual Pillar Assessments (all 6 pillars)."""
        
        logger.info("🏛️ STEP 2: Individual Pillar Assessments")
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
            
            # Assess each pillar individually
            for pillar in pillars:
                logger.info(f"🔍 Assessing {pillar} pillar")
                
                try:
                    # Get pillar questions
                    questions = self.question_framework.get_pillar_questions(pillar)
                    
                    # Perform enhanced capability-based assessment
                    from .server import assess_pillar_compliance
                    assessment = await assess_pillar_compliance(pillar, architecture_data)
                    
                    pillar_results[pillar] = {
                        "pillar": pillar,
                        "score": assessment.get("score", 0),
                        "risk_level": assessment.get("risk_level", "medium"),
                        "recommendations": assessment.get("recommendations", []),
                        "findings": assessment.get("findings", []),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    logger.info(f"✅ {pillar} assessment completed - Score: {assessment.get('score', 0)}")
                    
                except Exception as pillar_error:
                    logger.error(f"❌ {pillar} assessment failed: {pillar_error}")
                    pillar_results[pillar] = {
                        "pillar": pillar,
                        "error": str(pillar_error),
                        "score": 0,
                        "risk_level": "high"
                    }
            
            # Store in session
            session["pillar_assessments"] = pillar_results
            
            logger.info(f"✅ STEP 2 completed: All 6 pillars assessed")
            
            return {
                "success": True,
                "step": 2,
                "stage": WAFRStage.SOLUTION_PROPOSED.value,
                "data": pillar_results
            }
            
        except Exception as e:
            logger.error(f"❌ STEP 2 failed: {e}")
            return {"success": False, "step": 2, "error": str(e)}
    
    async def _step3_comprehensive_assessment(self, chat_id: str) -> Dict[str, Any]:
        """STEP 3: Comprehensive Assessment aggregation."""
        
        logger.info("📊 STEP 3: Comprehensive Assessment")
        session = self.get_session_state(chat_id)
        
        try:
            pillar_assessments = session.get("pillar_assessments", {})
            architecture_data = session.get("document_analysis", {})
            
            # Calculate overall scores
            valid_scores = []
            for pillar_data in pillar_assessments.values():
                if pillar_data.get("score") is not None:
                    score = pillar_data["score"]
                    converted_score = score * 10 if score <= 10 else score
                    valid_scores.append(converted_score)
            
            overall_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0
            overall_risk_level = "high" if overall_score < 60 else "medium" if overall_score < 80 else "low"
            
            # Generate high priority actions
            high_priority_actions = []
            for pillar_data in pillar_assessments.values():
                if pillar_data.get("recommendations"):
                    high_priority_actions.extend(pillar_data["recommendations"][:2])
            
            comprehensive_result = {
                "assessment_id": f"wafr-{chat_id}-{datetime.now().strftime('%Y%m%d')}",
                "chat_id": chat_id,
                "overall_score": overall_score,
                "overall_risk_level": overall_risk_level,
                "pillar_assessments": pillar_assessments,
                "document_analysis": architecture_data,
                "high_priority_actions": high_priority_actions[:8],
                "timestamp": datetime.now().isoformat()
            }
            
            # Store in session
            session["comprehensive_assessment"] = comprehensive_result
            
            logger.info(f"✅ STEP 3 completed: Overall score {overall_score:.1f}")
            
            return {
                "success": True,
                "step": 3,
                "stage": WAFRStage.SOLUTION_PROPOSED.value,
                "data": comprehensive_result
            }
            
        except Exception as e:
            logger.error(f"❌ STEP 3 failed: {e}")
            return {"success": False, "step": 3, "error": str(e)}
    
    async def _step4_professional_report(self, chat_id: str) -> Dict[str, Any]:
        """STEP 4: Professional Report generation."""
        
        logger.info("📋 STEP 4: Professional Report Generation")
        session = self.get_session_state(chat_id)
        
        try:
            # Transition: SOLUTION_PROPOSED → SOLUTION_FINALIZED
            if not self.transition_stage(chat_id, WAFRStage.SOLUTION_FINALIZED):
                return {"success": False, "error": "Invalid stage transition for report generation"}
            
            assessment_data = session.get("comprehensive_assessment", {})
            
            if not assessment_data:
                return {"success": False, "error": "No assessment data available for report generation"}
            
            # Generate report
            report_content = await self.report_generator.generate_report(assessment_data, ["all"])
            
            # Create report metadata
            report_result = {
                "report_generated": True,
                "chat_id": chat_id,
                "report_size": len(report_content) if report_content else 0,
                "generation_timestamp": datetime.now().isoformat(),
                "assessment_id": assessment_data.get("assessment_id"),
                "overall_score": assessment_data.get("overall_score", 0)
            }
            
            # Store in session
            session["report_data"] = report_result
            
            logger.info(f"✅ STEP 4 completed: Report generated ({len(report_content)} bytes)")
            
            return {
                "success": True,
                "step": 4,
                "stage": WAFRStage.SOLUTION_FINALIZED.value,
                "data": report_result
            }
            
        except Exception as e:
            logger.error(f"❌ STEP 4 failed: {e}")
            return {"success": False, "step": 4, "error": str(e)}
