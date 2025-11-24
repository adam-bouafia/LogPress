"""
Template Generator: Log alignment and schema extraction

This module extracts log schemas by:
1. Aligning multiple log entries
2. Identifying constant vs. variable positions
3. Generating templates with semantic field types

Example:
    Input logs:
        "[Thu Jun 09 06:07:04 2005] [notice] LDAP: Built with OpenLDAP"
        "[Thu Jun 09 06:07:05 2005] [notice] LDAP: SSL support unavailable"
    
    Output template:
        "[TIMESTAMP] [SEVERITY] LDAP: [MESSAGE]"
"""

from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field as dataclass_field
from collections import Counter, defaultdict
import re

from .tokenizer import LogTokenizer, Token, TokenType
from .semantic_types import SemanticTypeRecognizer, SemanticType, SemanticMatch


@dataclass
class LogTemplate:
    """Represents an extracted log schema template"""
    template_id: str
    pattern: List[str]  # Mix of constants and [SEMANTIC_TYPE]
    field_types: Dict[int, SemanticType]  # Position -> semantic type
    example_logs: List[str] = dataclass_field(default_factory=list)
    match_count: int = 0
    confidence: float = 0.0
    
    def __repr__(self):
        return f"Template({self.template_id}, matches={self.match_count}, pattern={' '.join(self.pattern[:5])}...)"
    
    def to_string(self) -> str:
        """Convert template to readable string"""
        return ' '.join(self.pattern)


@dataclass
class SchemaField:
    """Represents a field in the extracted schema"""
    position: int
    name: str
    semantic_type: SemanticType
    is_constant: bool
    constant_value: Optional[str] = None
    example_values: List[str] = dataclass_field(default_factory=list)


class TemplateGenerator:
    """
    Extract log schemas using alignment algorithm
    
    Process:
    1. Tokenize logs
    2. Group similar logs together
    3. Align tokens position by position
    4. Mark positions as CONSTANT (same across all) or VARIABLE (changes)
    5. Use semantic recognizer to classify variable positions
    6. Generate template with semantic types
    """
    
    def __init__(self, min_support: int = 3, similarity_threshold: float = 0.7):
        """
        Args:
            min_support: Minimum number of logs needed to form a template
            similarity_threshold: Similarity ratio for grouping logs (0-1)
        """
        self.tokenizer = LogTokenizer()
        self.recognizer = SemanticTypeRecognizer()
        self.min_support = min_support
        self.similarity_threshold = similarity_threshold
        self.templates: List[LogTemplate] = []
    
    def extract_schemas(self, log_lines: List[str]) -> List[LogTemplate]:
        """
        Extract schemas from a list of log entries
        
        Args:
            log_lines: List of raw log strings
            
        Returns:
            List of extracted templates, sorted by match count
        """
        if not log_lines:
            return []
        
        # Step 1: Tokenize all logs
        print(f"Tokenizing {len(log_lines)} logs...")
        tokenized_logs = []
        for i, log in enumerate(log_lines):
            if log.strip():
                tokens = self.tokenizer.tokenize(log)
                fields = self.tokenizer.get_fields(tokens)
                tokenized_logs.append({
                    'raw': log,
                    'tokens': tokens,
                    'fields': fields,
                    'index': i
                })
        
        # Step 2: Group logs by structure (similar token counts and patterns)
        print(f"Grouping {len(tokenized_logs)} logs by structure...")
        groups = self._group_by_structure(tokenized_logs)
        print(f"Found {len(groups)} structural groups")
        
        # Step 3: Generate templates for each group
        templates = []
        for group_id, group_logs in enumerate(groups):
            if len(group_logs) >= self.min_support:
                template = self._generate_template(group_logs, group_id)
                if template:
                    templates.append(template)
        
        # Sort by match count (most common first)
        templates.sort(key=lambda t: t.match_count, reverse=True)
        self.templates = templates
        
        return templates
    
    def _group_by_structure(self, tokenized_logs: List[Dict]) -> List[List[Dict]]:
        """
        Group logs with similar structure together
        
        Uses field count and token type patterns to group
        """
        groups = defaultdict(list)
        
        for log_data in tokenized_logs:
            # Create structure signature: field count + token types
            fields = log_data['fields']
            tokens = log_data['tokens']
            
            # Signature: number of fields + token type pattern
            token_types = tuple(t.type.value for t in tokens if t.type != TokenType.WHITESPACE)
            field_count = len(fields)
            
            signature = (field_count, token_types[:10])  # Use first 10 token types
            groups[signature].append(log_data)
        
        # Convert to list and filter by min_support
        return [logs for logs in groups.values() if len(logs) >= self.min_support]
    
    def _generate_template(self, group_logs: List[Dict], group_id: int) -> Optional[LogTemplate]:
        """
        Generate a template from a group of similar logs
        
        Algorithm:
        1. Align fields position by position
        2. For each position, check if constant or variable
        3. If constant and same across all logs -> keep literal
        4. If variable -> identify semantic type
        """
        if not group_logs:
            return None
        
        # Get fields from all logs in group
        all_fields = [log['fields'] for log in group_logs]
        
        # Find max field count
        max_fields = max(len(fields) for fields in all_fields)
        
        # Align fields position by position
        template_pattern = []
        field_types = {}
        
        for pos in range(max_fields):
            # Collect values at this position across all logs
            values_at_pos = []
            for fields in all_fields:
                if pos < len(fields):
                    values_at_pos.append(fields[pos])
            
            if not values_at_pos:
                continue
            
            # Check if constant (all same)
            unique_values = set(values_at_pos)
            
            if len(unique_values) == 1:
                # Constant field - use literal value
                constant_val = values_at_pos[0]
                # Still try to identify semantic type for metadata
                matches = self.recognizer.recognize(constant_val)
                if matches and matches[0].confidence > 0.80:
                    # High confidence semantic type even if constant
                    semantic_type = matches[0].type
                    template_pattern.append(f"[{semantic_type.value.upper()}]")
                    field_types[pos] = semantic_type
                else:
                    # Keep as literal constant
                    template_pattern.append(constant_val)
            
            elif len(unique_values) <= 3 and len(group_logs) >= 10:
                # Low cardinality - might be categorical field (like severity level)
                # Try semantic recognition
                sample_value = values_at_pos[0]
                matches = self.recognizer.recognize(sample_value)
                
                if matches and matches[0].confidence > 0.75:
                    semantic_type = matches[0].type
                    template_pattern.append(f"[{semantic_type.value.upper()}]")
                    field_types[pos] = semantic_type
                else:
                    # Low cardinality but unknown type
                    template_pattern.append("[FIELD]")
            
            else:
                # Variable field - identify semantic type
                # Sample multiple values to get best match
                sample_values = values_at_pos[:min(10, len(values_at_pos))]
                type_votes = defaultdict(int)
                
                for val in sample_values:
                    matches = self.recognizer.recognize(val)
                    if matches:
                        type_votes[matches[0].type] += matches[0].confidence
                
                if type_votes:
                    # Pick type with highest total confidence
                    best_type = max(type_votes.items(), key=lambda x: x[1])[0]
                    template_pattern.append(f"[{best_type.value.upper()}]")
                    field_types[pos] = best_type
                else:
                    # Unknown variable field
                    template_pattern.append("[FIELD]")
        
        # Create template
        template_id = f"T{group_id:03d}"
        example_logs = [log['raw'] for log in group_logs[:5]]  # Store first 5 as examples
        
        # Calculate confidence based on consistency
        confidence = len(group_logs) / (len(group_logs) + 10)  # Normalize by sample size
        
        return LogTemplate(
            template_id=template_id,
            pattern=template_pattern,
            field_types=field_types,
            example_logs=example_logs,
            match_count=len(group_logs),
            confidence=confidence
        )
    
    def match_log_to_template(self, log_line: str) -> Optional[Tuple[LogTemplate, Dict]]:
        """
        Match a log entry to an existing template
        
        Returns:
            Tuple of (matched_template, extracted_fields) or None if no match
        """
        tokens = self.tokenizer.tokenize(log_line)
        fields = self.tokenizer.get_fields(tokens)
        
        # Try to match against existing templates
        for template in self.templates:
            # Check if field count matches (approximately)
            template_field_count = len(template.pattern)
            if abs(len(fields) - template_field_count) <= 2:  # Allow small variance
                # Try to extract fields according to template
                extracted = {}
                for pos, pattern_part in enumerate(template.pattern):
                    if pos < len(fields):
                        if pattern_part.startswith('[') and pattern_part.endswith(']'):
                            # Variable field
                            field_type = pattern_part[1:-1]
                            extracted[field_type] = fields[pos]
                
                return (template, extracted)
        
        return None
    
    def get_schema_summary(self) -> Dict:
        """Get summary statistics of extracted schemas"""
        if not self.templates:
            return {}
        
        total_logs = sum(t.match_count for t in self.templates)
        
        return {
            'template_count': len(self.templates),
            'total_logs_matched': total_logs,
            'top_templates': [
                {
                    'id': t.template_id,
                    'pattern': t.to_string(),
                    'matches': t.match_count,
                    'coverage': t.match_count / total_logs if total_logs > 0 else 0
                }
                for t in self.templates[:10]
            ]
        }


# Example usage
if __name__ == "__main__":
    generator = TemplateGenerator(min_support=2)
    
    # Test with sample logs
    apache_logs = [
        "[Thu Jun 09 06:07:04 2005] [notice] LDAP: Built with OpenLDAP LDAP SDK",
        "[Thu Jun 09 06:07:04 2005] [notice] LDAP: SSL support unavailable",
        "[Thu Jun 09 06:07:05 2005] [error] env.createBean2(): Factory error creating channel.jni:jni",
        "[Thu Jun 09 06:07:05 2005] [error] config.update(): Can't create channel.jni:jni",
        "[Thu Jun 09 06:07:19 2005] [notice] Apache/2.0.49 (Fedora) configured -- resuming normal operations",
    ]
    
    healthapp_logs = [
        "20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579",
        "20171223-22:15:29:633|Step_StandReportReceiver|30002312|onReceive action: android.intent.action.SCREEN_ON",
        "20171223-22:15:29:635|Step_StandStepCounter|30002312|flush sensor data",
        "20171223-22:15:29:738|Step_LSC|30002312|onStandStepChanged 3579",
    ]
    
    print("="*70)
    print("Apache Logs Template Extraction")
    print("="*70)
    templates = generator.extract_schemas(apache_logs)
    for template in templates:
        print(f"\n{template}")
        print(f"Pattern: {template.to_string()}")
        print(f"Example: {template.example_logs[0][:80]}...")
    
    print("\n" + "="*70)
    print("HealthApp Logs Template Extraction")
    print("="*70)
    generator2 = TemplateGenerator(min_support=2)
    templates2 = generator2.extract_schemas(healthapp_logs)
    for template in templates2:
        print(f"\n{template}")
        print(f"Pattern: {template.to_string()}")
        print(f"Example: {template.example_logs[0][:80]}...")
