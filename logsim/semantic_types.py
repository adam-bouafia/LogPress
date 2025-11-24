"""
Semantic Types: Pattern-based recognition of semantic field types

This module provides regex patterns and confidence scoring for identifying:
- TIMESTAMP: Multiple formats (ISO, Unix epoch, syslog)
- IP_ADDRESS: IPv4/IPv6
- USER_ID, PROCESS_ID: Context-aware extraction
- ERROR_CODE, METRIC, STATUS: Domain-specific patterns
- MESSAGE: Free-text content

NO ML MODELS - pure pattern matching with heuristics
"""

import re
import regex  # Advanced regex with Unicode support
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum
from dateutil import parser as date_parser


class SemanticType(Enum):
    """Semantic field types found in logs"""
    TIMESTAMP = "timestamp"
    IP_ADDRESS = "ip_address"
    PORT = "port"
    USER_ID = "user_id"
    PROCESS_ID = "process_id"
    THREAD_ID = "thread_id"
    ERROR_CODE = "error_code"
    METRIC_VALUE = "metric_value"
    METRIC_UNIT = "metric_unit"
    STATUS = "status"
    SEVERITY = "severity"
    MODULE = "module"
    FUNCTION = "function"
    FILENAME = "filename"
    HOST = "host"
    URL = "url"
    ACTION = "action"
    MESSAGE = "message"
    REQUEST_ID = "request_id"
    UNKNOWN = "unknown"


@dataclass
class SemanticMatch:
    """Result of semantic type matching"""
    type: SemanticType
    value: str
    confidence: float  # 0.0 to 1.0
    pattern_name: str  # Which pattern matched
    start_pos: int = 0
    end_pos: int = 0
    
    def __repr__(self):
        return f"Match({self.type.value}, '{self.value[:30]}', conf={self.confidence:.2f})"


class SemanticTypeRecognizer:
    """
    Pattern-based semantic type recognition with confidence scoring
    
    Patterns are tested in priority order. Higher confidence = more specific pattern.
    """
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile all regex patterns for efficiency"""
        
        # TIMESTAMP patterns (most specific to least specific)
        self.timestamp_patterns = [
            # ISO 8601: 2024-11-23T10:15:32.123Z or 2024-11-23 10:15:32
            (re.compile(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:?\d{2})?'), 
             0.95, "iso8601"),
            
            # Unix timestamp with milliseconds: 1514038529606
            (re.compile(r'\b\d{13}\b'), 0.90, "unix_ms"),
            
            # Unix timestamp (10 digits)
            (re.compile(r'\b\d{10}\b'), 0.85, "unix_sec"),
            
            # Syslog format: Jun 09 06:07:04 or Thu Jun 09 06:07:04 2005
            (re.compile(r'\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)?\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\s+\d{4})?\b'),
             0.90, "syslog"),
            
            # Custom format: 20171223-22:15:29:606
            (re.compile(r'\b\d{8}-\d{2}:\d{2}:\d{2}:\d{3}\b'), 0.95, "custom_yyyymmdd"),
            
            # Time with milliseconds: 17:41:41,536
            (re.compile(r'\b\d{2}:\d{2}:\d{2}[,\.]\d{3,6}\b'), 0.85, "time_ms"),
            
            # Simple time: 10:15:32
            (re.compile(r'\b\d{2}:\d{2}:\d{2}\b'), 0.70, "time_simple"),
            
            # Short format: [10.30 16:49:06]
            (re.compile(r'\b\d{1,2}\.\d{2}\s+\d{2}:\d{2}:\d{2}\b'), 0.85, "short_datetime"),
        ]
        
        # IP ADDRESS patterns
        self.ip_patterns = [
            # IPv4
            (re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'), 0.95, "ipv4"),
            
            # IPv6 (simplified - full spec is complex)
            (re.compile(r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'), 0.95, "ipv6_full"),
            (re.compile(r'\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b'), 0.90, "ipv6_compressed"),
        ]
        
        # PORT patterns
        self.port_patterns = [
            (re.compile(r':(\d{1,5})\b'), 0.85, "port_colon"),  # :8080
            (re.compile(r'\bport[:\s=]+(\d{1,5})\b', re.IGNORECASE), 0.90, "port_keyword"),
        ]
        
        # SEVERITY/LEVEL patterns
        self.severity_patterns = [
            (re.compile(r'\b(DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|CRITICAL|TRACE|NOTICE)\b', re.IGNORECASE),
             0.95, "standard_levels"),
            (re.compile(r'\b(emerg|alert|crit|err|warning|notice|info|debug)\b', re.IGNORECASE),
             0.90, "syslog_levels"),
        ]
        
        # STATUS patterns
        self.status_patterns = [
            (re.compile(r'\b(success|successful|failed?|failure|timeout|denied|accepted|rejected|ok|error)\b', re.IGNORECASE),
             0.85, "common_status"),
            (re.compile(r'\bstatus:\s*(\d{3})\b', re.IGNORECASE),
             0.95, "http_status"),
        ]
        
        # ERROR_CODE patterns
        self.error_code_patterns = [
            (re.compile(r'\b(?:error|errno|err)[\s_-]?(?:code)?[:\s=]+([A-Z0-9_-]+)\b', re.IGNORECASE),
             0.95, "error_keyword"),
            (re.compile(r'\b[A-Z]{2,}[\s_-]?\d{3,}\b'),
             0.80, "uppercase_code"),
            (re.compile(r'\[ERR[0-9X]+\]', re.IGNORECASE),
             0.90, "bracketed_error"),
        ]
        
        # USER_ID patterns
        self.user_id_patterns = [
            (re.compile(r'\b(?:user|username|uid)[:\s=]+["\']?([a-zA-Z0-9_-]+)["\']?\b', re.IGNORECASE),
             0.95, "user_keyword"),
            (re.compile(r'\buid[:\s=]+(\d+)\b', re.IGNORECASE),
             0.90, "uid_numeric"),
        ]
        
        # PROCESS_ID patterns
        self.process_id_patterns = [
            (re.compile(r'\b(?:pid|process_id|proc)[:\s=]+(\d+)\b', re.IGNORECASE),
             0.95, "pid_keyword"),
            (re.compile(r'\[(\d{4,6})\]'),  # [2931] - likely PID in brackets
             0.75, "bracketed_number"),
        ]
        
        # METRIC patterns (value + unit)
        self.metric_patterns = [
            (re.compile(r'\b(\d+(?:\.\d+)?)\s*(ms|milliseconds?|seconds?|sec|minutes?|min|hours?|hrs?)\b', re.IGNORECASE),
             0.90, "time_metric"),
            (re.compile(r'\b(\d+(?:\.\d+)?)\s*(bytes?|KB|MB|GB|TB)\b', re.IGNORECASE),
             0.90, "size_metric"),
            (re.compile(r'\b(\d+(?:\.\d+)?)\s*(%|percent|CPU|memory|disk)\b', re.IGNORECASE),
             0.85, "percent_metric"),
        ]
        
        # MODULE/COMPONENT patterns
        self.module_patterns = [
            (re.compile(r'\b([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){2,})\b'),  # nova.compute.manager
             0.85, "dotted_module"),
            (re.compile(r'\b(Step_[A-Za-z]+)\b'),  # Step_LSC
             0.90, "prefixed_component"),
        ]
        
        # REQUEST_ID patterns
        self.request_id_patterns = [
            (re.compile(r'\[req-([a-f0-9-]{36,})\]', re.IGNORECASE),
             0.95, "bracketed_uuid"),
            (re.compile(r'\brequest[_-]?id[:\s=]+([a-zA-Z0-9-]+)\b', re.IGNORECASE),
             0.90, "request_keyword"),
        ]
        
        # FILENAME patterns
        self.filename_patterns = [
            (re.compile(r'\b([a-zA-Z0-9_-]+\.log(?:\.\d+)?(?:\.\d{4}-\d{2}-\d{2}_\d{2}:\d{2}:\d{2})?)\b'),
             0.90, "log_filename"),
            (re.compile(r'\b([a-zA-Z0-9_/-]+\.(?:py|java|c|cpp|js|conf|cfg))\b'),
             0.85, "source_file"),
        ]
        
        # HOST patterns
        self.host_patterns = [
            (re.compile(r'\b([a-z0-9-]+(?:\.[a-z0-9-]+)+\.[a-z]{2,})\b', re.IGNORECASE),
             0.90, "fqdn"),
            (re.compile(r'\b([a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+)\b'),
             0.75, "hostname"),
        ]
        
        # ACTION patterns
        self.action_patterns = [
            (re.compile(r'\b(start(?:ed|ing)?|stop(?:ped|ping)?|restart(?:ed|ing)?|open(?:ed|ing)?|clos(?:ed?|ing)|connect(?:ed|ing)?|disconnect(?:ed|ing)?)\b', re.IGNORECASE),
             0.80, "action_verb"),
        ]
    
    def recognize(self, field_value: str, context: Optional[Dict] = None) -> List[SemanticMatch]:
        """
        Identify semantic type(s) for a field value
        
        Args:
            field_value: The field content to analyze
            context: Optional context (previous/next fields, position in log)
            
        Returns:
            List of possible semantic matches, sorted by confidence (highest first)
        """
        if not field_value or not field_value.strip():
            return []
        
        matches = []
        
        # Try each pattern category
        matches.extend(self._match_patterns(field_value, self.timestamp_patterns, SemanticType.TIMESTAMP))
        matches.extend(self._match_patterns(field_value, self.ip_patterns, SemanticType.IP_ADDRESS))
        matches.extend(self._match_patterns(field_value, self.port_patterns, SemanticType.PORT))
        matches.extend(self._match_patterns(field_value, self.severity_patterns, SemanticType.SEVERITY))
        matches.extend(self._match_patterns(field_value, self.status_patterns, SemanticType.STATUS))
        matches.extend(self._match_patterns(field_value, self.error_code_patterns, SemanticType.ERROR_CODE))
        matches.extend(self._match_patterns(field_value, self.user_id_patterns, SemanticType.USER_ID))
        matches.extend(self._match_patterns(field_value, self.process_id_patterns, SemanticType.PROCESS_ID))
        matches.extend(self._match_patterns(field_value, self.metric_patterns, SemanticType.METRIC_VALUE))
        matches.extend(self._match_patterns(field_value, self.module_patterns, SemanticType.MODULE))
        matches.extend(self._match_patterns(field_value, self.request_id_patterns, SemanticType.REQUEST_ID))
        matches.extend(self._match_patterns(field_value, self.filename_patterns, SemanticType.FILENAME))
        matches.extend(self._match_patterns(field_value, self.host_patterns, SemanticType.HOST))
        matches.extend(self._match_patterns(field_value, self.action_patterns, SemanticType.ACTION))
        
        # Sort by confidence (highest first)
        matches.sort(key=lambda m: m.confidence, reverse=True)
        
        # If no matches, classify as MESSAGE (free text) with low confidence
        if not matches:
            matches.append(SemanticMatch(
                type=SemanticType.MESSAGE,
                value=field_value,
                confidence=0.50,
                pattern_name="default_message"
            ))
        
        return matches
    
    def _match_patterns(self, value: str, patterns: List[Tuple], semantic_type: SemanticType) -> List[SemanticMatch]:
        """Helper to match value against a list of patterns"""
        matches = []
        
        for pattern, confidence, pattern_name in patterns:
            match = pattern.search(value)
            if match:
                matched_value = match.group(1) if match.groups() else match.group(0)
                matches.append(SemanticMatch(
                    type=semantic_type,
                    value=matched_value,
                    confidence=confidence,
                    pattern_name=pattern_name,
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
        
        return matches
    
    def get_best_match(self, field_value: str, context: Optional[Dict] = None) -> SemanticMatch:
        """Get the single best semantic type match for a field"""
        matches = self.recognize(field_value, context)
        return matches[0] if matches else SemanticMatch(
            type=SemanticType.UNKNOWN,
            value=field_value,
            confidence=0.0,
            pattern_name="no_match"
        )


# Example usage
if __name__ == "__main__":
    recognizer = SemanticTypeRecognizer()
    
    # Test various field types
    test_fields = [
        "2024-11-23 10:15:32",
        "[Thu Jun 09 06:07:04 2005]",
        "192.168.1.1",
        "ERROR",
        "Step_LSC",
        "30002312",
        "nova.compute.manager",
        "[req-7a738b84-d574-43c6-a6c4-68c164365101]",
        "0.54 seconds",
        "proxy.cse.cuhk.edu.hk:5070",
        "Authentication failed for user admin",
    ]
    
    print("Semantic Type Recognition Test\n" + "="*50)
    for field in test_fields:
        print(f"\nField: {field}")
        matches = recognizer.recognize(field)
        print(f"Top matches:")
        for match in matches[:3]:  # Show top 3
            print(f"  {match}")
