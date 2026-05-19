"""
Service definition lookup tool for AWS pricing calculator agent
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional


class ServiceDefinitionTool:
    """Tool for looking up AWS service definitions by service name"""
    
    def __init__(self, definitions_path: Optional[str] = None):
        """
        Initialize the service definition tool
        
        Args:
            definitions_path: Path to service definitions directory. 
                            If None, uses default path relative to this file.
        """
        if definitions_path is None:
            # Go to the project root where service_definitions is located
            # From: awslabs/pricing_calculator_mcp_server/service_lookup.py
            # To:   service_definitions/
            current_dir = Path(__file__).parent.parent.parent
            self.definitions_path = current_dir / "service_definitions"
        else:
            self.definitions_path = Path(definitions_path)
        
        self.defs_path = self.definitions_path / "defs"
        self.mapping_file = self.definitions_path / "service_name_mapping.json"
        
        # Load service name mapping on initialization
        self.service_mapping = self._load_service_mapping()
    
    def _load_service_mapping(self) -> Dict[str, Dict[str, str]]:
        """Load the service name mapping file"""
        if not self.mapping_file.exists():
            return {}
        
        try:
            with open(self.mapping_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading service name mapping: {e}")
            return {}
    
    def _find_service_filename(self, service_name: str) -> Optional[str]:
        """
        Find the filename for a service based on various name matching strategies
        
        Args:
            service_name: The service name to search for
            
        Returns:
            The filename (without .json extension) if found, None otherwise
        """
        service_name_lower = service_name.lower()
        
        # Specific mappings for common service names that should always match correctly
        specific_mappings = {
            'amazon s3': 'amazonS3Standard',
            's3': 'amazonS3Standard',
            's3 standard': 'amazonS3Standard',
            'simple storage service': 'amazonS3Standard',
            'amazon simple storage service': 'amazonS3Standard',
            'amazon simple storage service (s3)': 'amazonS3Standard',
            'amazon kinesis firehose': 'amazonKinesisFirehose',
            'kinesis firehose': 'amazonKinesisFirehose',
            'amazon kinesis data firehose': 'amazonKinesisFirehose',
            'kinesis data firehose': 'amazonKinesisFirehose'
        }
        
        # Check specific mappings first
        if service_name_lower in specific_mappings:
            return specific_mappings[service_name_lower]
        
        # Strategy 1: Direct filename match
        potential_filename = service_name.replace(" ", "").replace("-", "").lower()
        if (self.defs_path / f"{potential_filename}.json").exists():
            return potential_filename
        
        # Strategy 2: Search in service mapping
        best_match = None
        best_score = 0
        
        for filename, service_info in self.service_mapping.items():
            original_name = service_info.get('original_name', '').lower()
            official_name = service_info.get('official_name', '').lower()
            
            # Exact match - highest priority
            if (service_name_lower == original_name or 
                service_name_lower == official_name):
                return filename
            
            # Check for high-quality partial matches
            words_service = set(service_name_lower.split())
            words_original = set(original_name.split())
            words_official = set(official_name.split())
            
            # Calculate match scores
            original_overlap = len(words_service & words_original)
            official_overlap = len(words_service & words_official)
            max_overlap = max(original_overlap, official_overlap)
            
            # Only consider matches with significant overlap
            if max_overlap >= 2 or any(word in words_original or word in words_official 
                                     for word in words_service if len(word) > 4):
                
                # Calculate a quality score
                score = max_overlap * 10  # Base score from word overlap
                
                # Bonus for exact substring matches
                if service_name_lower in original_name or service_name_lower in official_name:
                    score += 5
                
                # Penalty for extra words (prefer more specific matches)
                extra_words = len(words_original) + len(words_official) - len(words_service)
                score -= extra_words * 0.5
                
                # Update best match if this is better
                if score > best_score:
                    best_score = score
                    best_match = filename
        
        if best_match:
            return best_match
        
        # Strategy 3: Search in actual service definition files
        if self.defs_path.exists():
            for json_file in self.defs_path.glob("*.json"):
                try:
                    with open(json_file, 'r') as f:
                        service_data = json.load(f)
                        
                    # Check serviceName field
                    service_name_field = service_data.get('serviceName', '')
                    if isinstance(service_name_field, dict):
                        service_name_field = service_name_field.get('aws', '')
                    
                    if service_name_lower in service_name_field.lower():
                        return json_file.stem
                        
                except Exception:
                    continue
        
        return None
    
    def get_service_definition(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a single service definition by service name
        
        Args:
            service_name: The AWS service name to look up
            
        Returns:
            The service definition as a dictionary, or None if not found
        """
        filename = self._find_service_filename(service_name)
        if not filename:
            return None
        
        json_file = self.defs_path / f"{filename}.json"
        if not json_file.exists():
            return None
        
        try:
            with open(json_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading service definition for {service_name}: {e}")
            return None
    
    def get_service_definitions(self, service_names: List[str]) -> List[Dict[str, Any]]:
        """
        Get multiple service definitions by service names
        
        Args:
            service_names: List of AWS service names to look up
            
        Returns:
            List of service definition dictionaries. Missing services are omitted.
        """
        definitions = []
        
        for service_name in service_names:
            definition = self.get_service_definition(service_name)
            if definition:
                # Add metadata about which service name was requested
                definition['_requested_service_name'] = service_name
                definitions.append(definition)
            else:
                print(f"⚠️ Service definition not found for: {service_name}")
        
        return definitions
    
    def list_available_services(self) -> List[Dict[str, str]]:
        """
        List all available services with their names and filenames
        
        Returns:
            List of dictionaries with service information
        """
        services = []
        
        # From mapping file
        for filename, service_info in self.service_mapping.items():
            services.append({
                'filename': filename,
                'original_name': service_info.get('original_name', ''),
                'official_name': service_info.get('official_name', ''),
                'source': 'mapping'
            })
        
        # From definition files not in mapping
        if self.defs_path.exists():
            mapped_filenames = set(self.service_mapping.keys())
            
            for json_file in self.defs_path.glob("*.json"):
                if json_file.stem not in mapped_filenames:
                    try:
                        with open(json_file, 'r') as f:
                            service_data = json.load(f)
                        
                        service_name = service_data.get('serviceName', json_file.stem)
                        if isinstance(service_name, dict):
                            service_name = service_name.get('aws', json_file.stem)
                        
                        services.append({
                            'filename': json_file.stem,
                            'original_name': service_name,
                            'official_name': service_name,
                            'source': 'definition_file'
                        })
                        
                    except Exception:
                        continue
        
        return services
    
    def search_services(self, query: str) -> List[Dict[str, str]]:
        """
        Search for services by name or partial name match
        
        Args:
            query: Search query string
            
        Returns:
            List of matching service information dictionaries
        """
        query_lower = query.lower()
        all_services = self.list_available_services()
        
        matching_services = []
        
        for service in all_services:
            original_name = service.get('original_name', '').lower()
            official_name = service.get('official_name', '').lower()
            filename = service.get('filename', '').lower()
            
            if (query_lower in original_name or 
                query_lower in official_name or 
                query_lower in filename or
                original_name in query_lower or
                official_name in query_lower):
                matching_services.append(service)
        
        return matching_services


# Convenience function for direct usage
def get_service_definitions(service_names: List[str], definitions_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Convenience function to get service definitions
    
    Args:
        service_names: List of AWS service names to look up
        definitions_path: Optional path to service definitions directory
        
    Returns:
        List of service definition dictionaries
    """
    tool = ServiceDefinitionTool(definitions_path)
    return tool.get_service_definitions(service_names)


def search_service_definitions(query: str, definitions_path: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Convenience function to search for services
    
    Args:
        query: Search query string
        definitions_path: Optional path to service definitions directory
        
    Returns:
        List of matching service information dictionaries
    """
    tool = ServiceDefinitionTool(definitions_path)
    return tool.search_services(query)