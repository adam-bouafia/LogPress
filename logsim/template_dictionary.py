"""
Implements Otten's (2008) word-based dictionary replacement for log compression.

Based on: "Improvement of Log File Compression by Semantic Preprocessing" by Peter Otten
Reference: https://svn.nmap.org/nmap-exp/apo/thesis/otten-2008-thesis.pdf

Key technique: Replace frequently occurring words with unused ASCII byte codes
Otten's results: 14.82% compression improvement, 45.69% preprocessor filesize reduction

Scoring formula: score = frequency × (length - 1)
Rationale: Prioritize high-frequency AND long words for maximum compression gain
"""

import re
from collections import Counter
from typing import Dict, List, Tuple


class TemplateDictionary:
    """
    Per-template word dictionary for message field compression.
    
    Builds a custom dictionary mapping frequent words to unused ASCII bytes.
    Each template gets its own dictionary based on its message patterns.
    
    Example:
        Messages in template T001:
          "Connection from 192.168.1.1 established successfully"
          "Connection from 10.0.0.5 established successfully"
          "Connection from 172.16.0.1 established successfully"
        
        Dictionary built:
          'Connection' (freq=3, len=10) → score=27 → byte 0x01
          'established' (freq=3, len=11) → score=30 → byte 0x02
          'successfully' (freq=3, len=12) → score=33 → byte 0x03
          'from' (freq=3, len=4) → score=9 → byte 0x04
        
        Encoded message:
          "\x01 \x04 192.168.1.1 \x02 \x03" (much shorter!)
    """
    
    def __init__(self, template_id: str):
        self.template_id = template_id
        self.word_to_code: Dict[str, int] = {}  # word → byte code
        self.code_to_word: Dict[int, str] = {}  # byte code → word
        self.zero_freq_chars = self._find_unused_bytes()
    
    def _find_unused_bytes(self) -> List[int]:
        """
        Identify ASCII bytes (0-255) that are typically unused in text logs.
        
        Otten found ~160 unused characters in typical log files:
        - Control characters (0-31): Most unused except \n, \r, \t
        - Extended ASCII (128-255): Rarely used in English logs
        
        Returns:
            List of byte values available for dictionary encoding
        """
        # Start with control characters (0-31)
        unused = list(range(0, 32))
        
        # Add extended ASCII (128-255)
        unused += list(range(128, 256))
        
        # Exclude commonly used control characters
        excluded = {
            10,  # \n (newline)
            13,  # \r (carriage return)
            9,   # \t (tab)
        }
        
        return [b for b in unused if b not in excluded]
    
    def build_from_messages(self, messages: List[str], min_freq: int = 2):
        """
        Build dictionary from template message fields using Otten's scoring.
        
        Scoring formula: score = frequency × (length - 1)
        
        Why this works:
        - High frequency: Word appears often → more compression opportunities
        - Long words: Replacing 'successfully' (12 bytes) with 0x01 (1 byte) saves 11 bytes
        - Multiplying both: Balances frequency vs. length for optimal compression
        
        Args:
            messages: List of message strings from logs matching this template
            min_freq: Minimum frequency for a word to be included (default: 2)
        
        Example:
            messages = [
                "Connection established successfully",
                "Connection established successfully",
                "Connection failed",
            ]
            
            Word scores:
            - 'Connection' (freq=3, len=10): 3 × 9 = 27
            - 'established' (freq=2, len=11): 2 × 10 = 20
            - 'successfully' (freq=2, len=12): 2 × 11 = 22
            - 'failed' (freq=1, len=6): 1 × 5 = 5 (excluded if min_freq=2)
        """
        # Extract words (alphanumeric sequences of 2+ characters)
        word_freq = Counter()
        for msg in messages:
            # Find words: 2+ alphanumeric characters
            words = re.findall(r'\b\w{2,}\b', msg)
            word_freq.update(words)
        
        # Score each word: frequency × (length - 1)
        scored: List[Tuple[str, int]] = []
        for word, freq in word_freq.items():
            if freq >= min_freq:
                score = freq * (len(word) - 1)
                scored.append((word, score))
        
        # Sort by score (highest first)
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Map top N words to unused bytes (N = available zero-frequency characters)
        available_bytes = len(self.zero_freq_chars)
        for i, (word, score) in enumerate(scored[:available_bytes]):
            code = self.zero_freq_chars[i]
            self.word_to_code[word] = code
            self.code_to_word[code] = word
    
    def encode_message(self, message: str) -> bytes:
        """
        Replace dictionary words with single-byte codes.
        
        Strategy: Replace longest words first to avoid partial matches.
        Example: "Connection" before "Connect" to prevent "Connectionion"
        
        Args:
            message: Original message string
        
        Returns:
            Encoded message as bytes (using latin-1 to preserve byte values)
        
        Example:
            message = "Connection established successfully"
            dictionary = {'Connection': 0x01, 'established': 0x02, 'successfully': 0x03}
            
            Output: b'\x01 \x02 \x03'
        """
        if not self.word_to_code:
            # No dictionary built yet
            return message.encode('utf-8')
        
        # Sort words by length (longest first) to prevent partial matches
        sorted_words = sorted(self.word_to_code.keys(), key=len, reverse=True)
        
        result = message
        for word in sorted_words:
            if word in result:
                # Replace word with byte code (as single character)
                code_char = chr(self.word_to_code[word])
                result = result.replace(word, code_char)
        
        # Encode as latin-1 to preserve byte values (0-255)
        return result.encode('latin-1')
    
    def decode_message(self, binary: bytes) -> str:
        """
        Reverse encoding: replace byte codes with original words.
        
        Args:
            binary: Encoded message bytes
        
        Returns:
            Original message string
        
        Example:
            binary = b'\x01 \x02 \x03'
            dictionary = {0x01: 'Connection', 0x02: 'established', 0x03: 'successfully'}
            
            Output: "Connection established successfully"
        """
        # Decode from latin-1 to preserve byte values
        try:
            result = binary.decode('latin-1')
        except UnicodeDecodeError:
            # Fallback to UTF-8 if latin-1 fails
            result = binary.decode('utf-8', errors='replace')
        
        # Replace byte codes with original words
        for code, word in self.code_to_word.items():
            code_char = chr(code)
            if code_char in result:
                result = result.replace(code_char, word)
        
        return result
    
    def get_stats(self) -> Dict:
        """
        Get dictionary statistics for analysis.
        
        Returns:
            Dictionary with:
            - num_words: Number of words in dictionary
            - avg_word_length: Average length of dictionary words
            - available_bytes: Total unused bytes available
            - utilization: Percentage of available bytes used
        """
        if not self.word_to_code:
            return {
                'num_words': 0,
                'avg_word_length': 0.0,
                'available_bytes': len(self.zero_freq_chars),
                'utilization': 0.0,
            }
        
        total_length = sum(len(word) for word in self.word_to_code.keys())
        avg_length = total_length / len(self.word_to_code)
        utilization = (len(self.word_to_code) / len(self.zero_freq_chars)) * 100
        
        return {
            'num_words': len(self.word_to_code),
            'avg_word_length': avg_length,
            'available_bytes': len(self.zero_freq_chars),
            'utilization': utilization,
        }


# Quick test
if __name__ == '__main__':
    # Test with sample log messages
    test_messages = [
        "Connection from 192.168.1.1 established successfully",
        "Connection from 10.0.0.5 established successfully",
        "Connection from 172.16.0.1 established successfully",
        "Connection from 192.168.1.100 established with timeout",
        "Connection from 10.0.0.10 established with delay",
        "Authentication failed for user admin",
        "Authentication failed for user root",
        "Authentication successful for user alice",
    ]
    
    print("=== Template Dictionary Test ===\n")
    print(f"Test corpus: {len(test_messages)} messages\n")
    
    # Build dictionary
    template_dict = TemplateDictionary("T001")
    template_dict.build_from_messages(test_messages, min_freq=2)
    
    # Show dictionary contents
    print("Dictionary built (top words by score):")
    scored = [
        (word, code, len(word))
        for word, code in template_dict.word_to_code.items()
    ]
    scored.sort(key=lambda x: x[2], reverse=True)  # Sort by word length
    
    for word, code, length in scored[:10]:  # Show top 10
        print(f"  '{word}' (len={length}) → byte 0x{code:02x}")
    
    print(f"\nStats: {template_dict.get_stats()}")
    
    # Test encoding/decoding
    print("\n=== Encoding Test ===\n")
    test_msg = test_messages[0]
    encoded = template_dict.encode_message(test_msg)
    decoded = template_dict.decode_message(encoded)
    
    size_reduction = len(test_msg) - len(encoded)
    reduction_pct = (size_reduction / len(test_msg)) * 100
    
    print(f"Original: {test_msg}")
    print(f"  Size: {len(test_msg)} bytes")
    print(f"\nEncoded: {encoded.hex()}")
    print(f"  Size: {len(encoded)} bytes")
    print(f"\nDecoded: {decoded}")
    print(f"  Match: {decoded == test_msg}")
    print(f"\nCompression: {size_reduction} bytes saved ({reduction_pct:.1f}% reduction)")
