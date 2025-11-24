"""
Tokenizer: Smart log tokenization that handles varied formats

This module splits log entries intelligently, recognizing:
- Brackets: [timestamp], [severity]
- Pipes: field1|field2|field3
- Timestamps in multiple formats
- Quoted strings
- URLs and file paths
- Numbers and metrics
"""

import re
from typing import List, Tuple, Dict
from dataclasses import dataclass
from enum import Enum


class TokenType(Enum):
    """Types of tokens that can be extracted from logs"""
    BRACKET = "bracket"          # [content]
    QUOTED = "quoted"            # "content" or 'content'
    PIPE_DELIMITED = "pipe"      # field|field|field
    WHITESPACE = "whitespace"    # spaces/tabs
    WORD = "word"                # plain text
    NUMBER = "number"            # 123, 45.67
    PUNCTUATION = "punctuation"  # : , - etc
    UNKNOWN = "unknown"


@dataclass
class Token:
    """Represents a single token from a log entry"""
    type: TokenType
    value: str
    start_pos: int
    end_pos: int
    
    def __repr__(self):
        return f"Token({self.type.value}, '{self.value[:20]}...', {self.start_pos}-{self.end_pos})"


class LogTokenizer:
    """
    Smart tokenizer for log entries
    
    Handles multiple log formats:
    - Apache: [timestamp] [severity] message
    - HealthApp: timestamp|component|pid|message
    - Zookeeper: timestamp - LEVEL [thread:class@line] - message
    - OpenStack: filename timestamp pid LEVEL module [req-id] message
    - Proxifier: [timestamp] process - host:port action, metrics
    """
    
    # Pattern for bracketed content: [...]
    BRACKET_PATTERN = re.compile(r'\[([^\]]+)\]')
    
    # Pattern for quoted strings: "..." or '...'
    QUOTED_PATTERN = re.compile(r'["\']([^"\']*)["\']')
    
    # Pattern for numbers (integers and floats)
    NUMBER_PATTERN = re.compile(r'\b\d+(?:\.\d+)?\b')
    
    # Pattern for pipe-delimited format (check if line has multiple pipes)
    PIPE_DELIMITED_PATTERN = re.compile(r'^([^|]+\|){2,}')
    
    def tokenize(self, log_line: str) -> List[Token]:
        """
        Tokenize a log entry into structured tokens
        
        Args:
            log_line: Raw log entry string
            
        Returns:
            List of Token objects representing the parsed log
        """
        if not log_line or not log_line.strip():
            return []
        
        # Check if pipe-delimited format (like HealthApp)
        if self.PIPE_DELIMITED_PATTERN.match(log_line):
            return self._tokenize_pipe_delimited(log_line)
        
        # Otherwise use general tokenization
        return self._tokenize_general(log_line)
    
    def _tokenize_pipe_delimited(self, log_line: str) -> List[Token]:
        """Handle pipe-delimited logs like HealthApp"""
        tokens = []
        fields = log_line.split('|')
        
        pos = 0
        for i, field in enumerate(fields):
            if i > 0:
                # Add pipe as punctuation
                tokens.append(Token(
                    type=TokenType.PIPE_DELIMITED,
                    value='|',
                    start_pos=pos,
                    end_pos=pos + 1
                ))
                pos += 1
            
            field_value = field.strip()
            tokens.append(Token(
                type=TokenType.WORD,
                value=field_value,
                start_pos=pos,
                end_pos=pos + len(field)
            ))
            pos += len(field)
        
        return tokens
    
    def _tokenize_general(self, log_line: str) -> List[Token]:
        """
        General tokenization for bracket-based and space-delimited logs
        
        Priority:
        1. Extract bracketed content first: [...]
        2. Extract quoted strings: "..." or '...'
        3. Split remaining by whitespace
        4. Classify each token (number, word, punctuation)
        """
        tokens = []
        remaining = log_line
        offset = 0
        
        # Extract brackets and quoted strings first
        special_tokens = []
        
        # Find all bracketed content
        for match in self.BRACKET_PATTERN.finditer(log_line):
            special_tokens.append((match.start(), match.end(), 'bracket', match.group(0)))
        
        # Find all quoted strings
        for match in self.QUOTED_PATTERN.finditer(log_line):
            # Check if not inside a bracket
            inside_bracket = any(
                start <= match.start() < end 
                for start, end, ttype, _ in special_tokens 
                if ttype == 'bracket'
            )
            if not inside_bracket:
                special_tokens.append((match.start(), match.end(), 'quoted', match.group(0)))
        
        # Sort by position
        special_tokens.sort()
        
        # Build tokens
        last_pos = 0
        for start, end, token_type, value in special_tokens:
            # Process text before this special token
            if start > last_pos:
                before_text = log_line[last_pos:start]
                tokens.extend(self._tokenize_plain_text(before_text, last_pos))
            
            # Add the special token
            if token_type == 'bracket':
                tokens.append(Token(
                    type=TokenType.BRACKET,
                    value=value,
                    start_pos=start,
                    end_pos=end
                ))
            elif token_type == 'quoted':
                tokens.append(Token(
                    type=TokenType.QUOTED,
                    value=value,
                    start_pos=start,
                    end_pos=end
                ))
            
            last_pos = end
        
        # Process remaining text after last special token
        if last_pos < len(log_line):
            tokens.extend(self._tokenize_plain_text(log_line[last_pos:], last_pos))
        
        return tokens
    
    def _tokenize_plain_text(self, text: str, offset: int) -> List[Token]:
        """Tokenize plain text (no brackets or quotes) by whitespace"""
        tokens = []
        
        # Split by whitespace but keep track of positions
        parts = re.split(r'(\s+)', text)
        pos = offset
        
        for part in parts:
            if not part:
                continue
            
            if part.isspace():
                tokens.append(Token(
                    type=TokenType.WHITESPACE,
                    value=part,
                    start_pos=pos,
                    end_pos=pos + len(part)
                ))
            elif self.NUMBER_PATTERN.fullmatch(part):
                tokens.append(Token(
                    type=TokenType.NUMBER,
                    value=part,
                    start_pos=pos,
                    end_pos=pos + len(part)
                ))
            elif part in ',:;-':
                tokens.append(Token(
                    type=TokenType.PUNCTUATION,
                    value=part,
                    start_pos=pos,
                    end_pos=pos + len(part)
                ))
            else:
                tokens.append(Token(
                    type=TokenType.WORD,
                    value=part,
                    start_pos=pos,
                    end_pos=pos + len(part)
                ))
            
            pos += len(part)
        
        return tokens
    
    def get_fields(self, tokens: List[Token]) -> List[str]:
        """
        Extract field values from tokens (ignoring whitespace/punctuation)
        
        Useful for schema extraction
        """
        fields = []
        for token in tokens:
            if token.type in (TokenType.BRACKET, TokenType.QUOTED, TokenType.WORD, 
                            TokenType.NUMBER):
                # Extract content from brackets/quotes
                if token.type == TokenType.BRACKET:
                    fields.append(token.value[1:-1])  # Remove [ ]
                elif token.type == TokenType.QUOTED:
                    fields.append(token.value[1:-1])  # Remove " " or ' '
                else:
                    fields.append(token.value)
        
        return fields


# Example usage
if __name__ == "__main__":
    tokenizer = LogTokenizer()
    
    # Test with different log formats
    test_logs = [
        "[Thu Jun 09 06:07:04 2005] [notice] LDAP: Built with OpenLDAP LDAP SDK",
        "20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579",
        "2015-07-29 17:41:41,536 - INFO  [main:QuorumPeerConfig@101] - Reading configuration",
        "[10.30 16:49:06] chrome.exe - proxy.cse.cuhk.edu.hk:5070 close, 0 bytes sent"
    ]
    
    for log in test_logs:
        print(f"\nLog: {log[:80]}...")
        tokens = tokenizer.tokenize(log)
        print(f"Tokens ({len(tokens)}):")
        for token in tokens[:10]:  # Show first 10
            print(f"  {token}")
        
        fields = tokenizer.get_fields(tokens)
        print(f"Fields: {fields[:5]}")  # Show first 5
