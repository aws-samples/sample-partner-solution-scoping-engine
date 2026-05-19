# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.

"""Data models for SOW Generator MCP Server."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator


class SOWTemplateType(str, Enum):
    """Available SOW template types."""
    
    AWS_MAP = "aws_map"
    AWS_MODERNIZATION = "aws_modernization"
    STANDARD_MIGRATION = "standard_migration"


class ProjectRole(str, Enum):
    """Available project roles with standard rates."""
    
    CLOUD_ARCHITECT = "Cloud Architect"
    CLOUD_ENGINEER = "Cloud Engineer"
    SOLUTIONS_ARCHITECT = "Solutions Architect"
    DEVOPS_ENGINEER = "DevOps Engineer"
    SCRUM_MASTER = "Scrum Master"
    DATA_ENGINEER = "Data Engineer"
    SECURITY_ENGINEER = "Security Engineer"


class LaborRates(BaseModel):
    """Labor rates configuration for different roles."""
    
    rates: Dict[str, float] = Field(
        default={
            "Cloud Architect": 265.00,
            "Cloud Engineer": 190.00,
            "Solutions Architect": 250.00,
            "DevOps Engineer": 180.00,
            "Scrum Master": 210.00,
            "Data Engineer": 200.00,
            "Security Engineer": 220.00,
        },
        description="Hourly rates for different project roles"
    )


class ProjectPersonnel(BaseModel):
    """Project personnel information."""
    
    role: str = Field(..., description="Role title (e.g., 'Cloud Architect', 'Scrum Master')")
    name: Optional[str] = Field(None, description="Person's name (optional, can be 'TBD')")
    responsibility: Optional[str] = Field("", description="Key responsibilities for this role")
    hours_per_sprint: int = Field(..., description="Estimated hours per sprint", ge=1)
    total_sprints: int = Field(3, description="Total number of sprints", ge=1)
    
    @property
    def total_hours(self) -> int:
        """Calculate total hours for this role."""
        return self.hours_per_sprint * self.total_sprints


class SOWMetadata(BaseModel):
    """Metadata for SOW generation."""
    
    chat_id: str = Field(..., description="Unique chat identifier")
    customer_name: str = Field(..., description="Customer company name")
    project_title: str = Field(..., description="Project title")
    project_description: str = Field(..., description="Detailed project description")
    project_objective: Optional[str] = Field(None, description="Project objective")
    project_timeline: Optional[List[Dict[str, Any]]] = Field(None, description="Project timeline phases")
    template_type: str = Field("aws_map", description="SOW template type")
    effective_date: Optional[datetime] = Field(None, description="SOW effective date")
    partner_name: str = Field("ExamplePartner", description="Partner company name")
    
    @validator('effective_date', pre=True, always=True)
    def set_effective_date(cls, v):
        """Set effective date to today if not provided."""
        return v or datetime.now()


class ProjectCosts(BaseModel):
    """Project cost breakdown."""
    
    personnel: List[ProjectPersonnel] = Field(..., description="Project personnel list")
    labor_rates: LaborRates = Field(default_factory=LaborRates, description="Labor rates")
    additional_costs: Dict[str, float] = Field(default_factory=dict, description="Additional costs")
    
    @property
    def total_labor_cost(self) -> float:
        """Calculate total labor cost."""
        total = 0.0
        for person in self.personnel:
            rate = self.labor_rates.rates.get(person.role, 0.0)
            total += rate * person.total_hours
        return total
    
    @property
    def total_additional_cost(self) -> float:
        """Calculate total additional costs."""
        return sum(self.additional_costs.values())
    
    @property
    def total_project_cost(self) -> float:
        """Calculate total project cost."""
        return self.total_labor_cost + self.total_additional_cost


class SOWDeliverable(BaseModel):
    """SOW deliverable item."""
    
    name: str = Field(..., description="Deliverable name")
    description: str = Field(..., description="Detailed description of the deliverable")


class SOWRequest(BaseModel):
    """Complete SOW generation request."""
    
    metadata: SOWMetadata = Field(..., description="SOW metadata")
    personnel: List[ProjectPersonnel] = Field(..., description="Project personnel")
    deliverables: List[SOWDeliverable] = Field(..., description="Project deliverables")
    assumptions: List[str] = Field(default_factory=list, description="Project assumptions")
    exclusions: List[str] = Field(default_factory=list, description="Project exclusions")
    labor_rates: Optional[LaborRates] = Field(None, description="Custom labor rates")
    
    @property
    def project_costs(self) -> ProjectCosts:
        """Get project costs calculation."""
        rates = self.labor_rates or LaborRates()
        return ProjectCosts(personnel=self.personnel, labor_rates=rates)


class SOWGenerationResult(BaseModel):
    """Result of SOW generation."""
    
    status: str = Field(..., description="Generation status (success/error)")
    chat_id: Optional[str] = Field(None, description="Chat ID used for generation")
    s3_url: Optional[str] = Field(None, description="S3 URL of generated SOW PDF")
    s3_key: Optional[str] = Field(None, description="S3 key for the SOW PDF")
    version_id: Optional[str] = Field(None, description="S3 version ID")
    message: str = Field(..., description="Status message")
    file_size: Optional[int] = Field(None, description="Generated file size in bytes")
    generation_time: Optional[float] = Field(None, description="Time taken to generate (seconds)")
    error_details: Optional[str] = Field(None, description="Error details if generation failed")