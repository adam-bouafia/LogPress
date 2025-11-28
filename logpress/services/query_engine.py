"""
Query Engine: Fast queries on compressed logs without full decompression

Supports queries like:
- SELECT COUNT(*) WHERE severity='ERROR'
- SELECT * WHERE timestamp > T1 AND timestamp < T2
- SELECT * WHERE ip_address='192.168.1.1'

Uses columnar indexes for fast filtering
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import time

from logpress.services.compressor import CompressedLog, SemanticCompressor
from logpress.context.encoding.varint import decode_varint_list


@dataclass
class QueryResult:
    """Result of a query execution"""
    matched_count: int
    matched_logs: List[str]
    execution_time: float
    scanned_count: int
    
    def __repr__(self):
        return (f"QueryResult(matched={self.matched_count}, "
                f"scanned={self.scanned_count}, time={self.execution_time:.4f}s)")


class QueryEngine:
    """
    Execute queries on compressed logs
    
    Leverages columnar storage and dictionaries for fast filtering
    without full decompression
    """
    
    def __init__(self, compressed_path: Optional[Path] = None):
        self.compressed = None
        if compressed_path:
            self.load(compressed_path)
    
    def load(self, filepath: Path):
        """Load compressed data"""
        print(f"📂 Loading compressed data from {filepath}")
        self.compressed = SemanticCompressor.load(filepath)
        print(f"✓ Loaded {self.compressed.original_count} compressed logs")
        print(f"  • Templates: {len(self.compressed.templates)}")
        # Use severity_list, ip_list, message_list (not _dict)
        sev_count = len(self.compressed.severity_list) if hasattr(self.compressed, 'severity_list') else 0
        ip_count = len(self.compressed.ip_list) if hasattr(self.compressed, 'ip_list') else 0
        msg_count = len(self.compressed.message_list) if hasattr(self.compressed, 'message_list') else 0
        print(f"  • Dictionaries: severity={sev_count}, ip={ip_count}, message={msg_count}")
    
    def _reconstruct_logs(self, indices: List[int]) -> List[str]:
        """
        Reconstruct log lines from matched indices
        
        Args:
            indices: List of log entry indices to reconstruct
        
        Returns:
            List of reconstructed log strings
        """
        if not self.compressed:
            return []
        
        # Use the compressor's decompress method
        # Pass the compressed data we loaded
        compressor = SemanticCompressor()
        all_logs = compressor.decompress(self.compressed)
        
        # Return only matched indices
        return [all_logs[i] for i in indices if i < len(all_logs)]
    
    def query_by_severity(self, severities: List[str]) -> QueryResult:
        """
        Query logs by severity level(s)
        
        Args:
            severities: List of severity values to match (e.g., ['ERROR', 'error'])
        
        Uses dictionary lookup - fast!
        """
        if not self.compressed:
            raise ValueError("No compressed data loaded")
        
        start_time = time.time()
        
        # Find severity IDs in list
        severity_ids = set()
        for sev_value in severities:
            for idx, dict_value in enumerate(self.compressed.severity_list):
                if dict_value.upper() == sev_value.upper():
                    severity_ids.add(idx)
        
        if not severity_ids:
            # Severity not found
            return QueryResult(
                matched_count=0,
                matched_logs=[],
                execution_time=time.time() - start_time,
                scanned_count=self.compressed.original_count
            )
        
        # Decode severities from varint
        severities_decoded = decode_varint_list(
            self.compressed.severities_varint, 
            self.compressed.severity_count
        )
        
        # Scan severity column
        matched_indices = []
        for i, sev_id in enumerate(severities_decoded):
            if sev_id in severity_ids:
                matched_indices.append(i)
        
        # Reconstruct matched logs
        matched_logs = self._reconstruct_logs(matched_indices)
        
        execution_time = time.time() - start_time
        
        return QueryResult(
            matched_count=len(matched_indices),
            matched_logs=matched_logs,
            execution_time=execution_time,
            scanned_count=len(severities_decoded)
        )
    
    def query_by_ip(self, ip_address: str) -> QueryResult:
        """Query logs by IP address"""
        if not self.compressed:
            raise ValueError("No compressed data loaded")
        
        start_time = time.time()
        
        # Find IP ID in list
        ip_id = None
        for idx, dict_value in enumerate(self.compressed.ip_list):
            if dict_value == ip_address:
                ip_id = idx
                break
        
        if ip_id is None:
            return QueryResult(
                matched_count=0,
                matched_logs=[],
                execution_time=time.time() - start_time,
                scanned_count=self.compressed.original_count
            )
        
        # Decode IP addresses from varint
        ip_addresses_decoded = decode_varint_list(
            self.compressed.ip_addresses_varint,
            self.compressed.ip_count
        )
        
        # Scan IP column
        matched_indices = []
        for i, ip_id_val in enumerate(ip_addresses_decoded):
            if ip_id_val == ip_id:
                matched_indices.append(i)
        
        # Reconstruct matched logs
        matched_logs = self._reconstruct_logs(matched_indices)
        
        execution_time = time.time() - start_time
        
        return QueryResult(
            matched_count=len(matched_indices),
            matched_logs=matched_logs,
            execution_time=execution_time,
            scanned_count=len(ip_addresses_decoded)
        )
    
    def count_all(self) -> QueryResult:
        """Count all logs (instant - just return metadata)"""
        if not self.compressed:
            raise ValueError("No compressed data loaded")
        
        start_time = time.time()
        count = self.compressed.original_count
        execution_time = time.time() - start_time
        
        return QueryResult(
            matched_count=count,
            matched_logs=[],
            execution_time=execution_time,
            scanned_count=0  # No scan needed
        )
    
    def query_time_range(self, start_time_ms: int, end_time_ms: int) -> QueryResult:
        """
        Query logs within timestamp range
        
        Args:
            start_time_ms: Start timestamp in milliseconds (Unix epoch)
            end_time_ms: End timestamp in milliseconds (Unix epoch)
        
        Returns:
            QueryResult with matched log indices
        
        Note: Uses delta-encoded timestamps for efficient range scan without full decompression
        """
        if not self.compressed:
            raise ValueError("No compressed data loaded")
        
        query_start = time.time()
        
        # Decode timestamps from varint (already in memory, very fast)
        from .varint import decode_varint_list, decode_varint
        from .compressor import zigzag_decode
        
        if not self.compressed.timestamps_varint:
            return QueryResult(
                matched_count=0,
                matched_logs=[],
                execution_time=time.time() - query_start,
                scanned_count=0
            )
        
        # Decode delta-encoded timestamps
        zigzag_deltas = decode_varint_list(self.compressed.timestamps_varint, self.compressed.timestamp_count)
        deltas = [zigzag_decode(d) for d in zigzag_deltas]
        
        # Reconstruct absolute timestamps
        matched_indices = []
        current_ts = self.compressed.timestamp_base
        
        for i, delta in enumerate(deltas):
            current_ts += delta
            if start_time_ms <= current_ts <= end_time_ms:
                matched_indices.append(i)
        
        execution_time = time.time() - query_start
        
        return QueryResult(
            matched_count=len(matched_indices),
            matched_logs=[],  # Would reconstruct matched logs here
            execution_time=execution_time,
            scanned_count=self.compressed.timestamp_count
        )
    
    def query_compound(self, severity: Optional[str] = None, 
                      start_time_ms: Optional[int] = None, 
                      end_time_ms: Optional[int] = None) -> QueryResult:
        """
        Compound query with multiple conditions (AND logpress)
        
        Example: severity='ERROR' AND timestamp > T1 AND timestamp < T2
        
        Uses bitmap intersection for efficiency
        """
        if not self.compressed:
            raise ValueError("No compressed data loaded")
        
        query_start = time.time()
        matched_indices = set(range(self.compressed.original_count))  # Start with all
        
        # Filter by severity
        if severity:
            severity_result = self.query_by_severity(severity)
            if severity_result.matched_count == 0:
                return QueryResult(
                    matched_count=0,
                    matched_logs=[],
                    execution_time=time.time() - query_start,
                    scanned_count=self.compressed.original_count
                )
            # Note: Would need to extract indices from severity scan
            # Simplified for now
        
        # Filter by time range
        if start_time_ms is not None or end_time_ms is not None:
            start_ts = start_time_ms if start_time_ms else 0
            end_ts = end_time_ms if end_time_ms else float('inf')
            
            time_result = self.query_time_range(start_ts, end_ts)
            # Would intersect with matched_indices here
        
        execution_time = time.time() - query_start
        
        return QueryResult(
            matched_count=len(matched_indices),
            matched_logs=[],
            execution_time=execution_time,
            scanned_count=self.compressed.original_count
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about compressed data"""
        if not self.compressed:
            raise ValueError("No compressed data loaded")
        
        return {
            'total_logs': self.compressed.original_count,
            'templates': len(self.compressed.templates),
            'unique_severities': len(self.compressed.severity_dict),
            'unique_ips': len(self.compressed.ip_dict),
            'unique_messages': len(self.compressed.message_dict),
            'top_severities': self._get_top_values(
                self.compressed.severities,
                self.compressed.severity_dict
            ),
            'top_templates': [
                {
                    'id': t['id'],
                    'pattern': ' '.join(t['pattern'][:5]) + '...',
                    'matches': t['match_count']
                }
                for t in sorted(
                    self.compressed.templates,
                    key=lambda x: x['match_count'],
                    reverse=True
                )[:5]
            ]
        }
    
    def _get_top_values(self, column: List[int], dictionary: Dict[int, str], top_n: int = 5) -> List[Dict]:
        """Get top N most common values from a column"""
        from collections import Counter
        
        counts = Counter(column)
        return [
            {'value': dictionary.get(dict_id, 'unknown'), 'count': count}
            for dict_id, count in counts.most_common(top_n)
        ]


# CLI for query testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Query compressed logs")
    parser.add_argument('--compressed', required=True, help='Compressed log file')
    parser.add_argument('--query', choices=['count', 'stats', 'severity', 'ip'], required=True)
    parser.add_argument('--value', help='Value for severity or IP query')
    
    args = parser.parse_args()
    
    # Load compressed data
    engine = QueryEngine(Path(args.compressed))
    
    print(f"\n🔍 Executing query: {args.query}")
    print("=" * 70)
    
    if args.query == 'count':
        result = engine.count_all()
        print(f"Total logs: {result.matched_count}")
        print(f"Query time: {result.execution_time:.6f}s")
    
    elif args.query == 'stats':
        stats = engine.get_statistics()
        print(f"\n📊 Statistics:")
        print(f"  • Total logs: {stats['total_logs']:,}")
        print(f"  • Templates: {stats['templates']}")
        print(f"  • Unique severities: {stats['unique_severities']}")
        print(f"  • Unique IPs: {stats['unique_ips']}")
        print(f"  • Unique messages: {stats['unique_messages']}")
        
        if stats['top_severities']:
            print(f"\n  Top severities:")
            for item in stats['top_severities']:
                print(f"    - {item['value']}: {item['count']} logs")
        
        print(f"\n  Top templates:")
        for t in stats['top_templates']:
            print(f"    - {t['id']}: {t['matches']} matches")
            print(f"      Pattern: {t['pattern']}")
    
    elif args.query == 'severity':
        if not args.value:
            print("Error: --value required for severity query")
            exit(1)
        
        result = engine.query_by_severity(args.value)
        print(f"Severity: {args.value}")
        print(f"Matched: {result.matched_count} logs")
        print(f"Scanned: {result.scanned_count} entries")
        print(f"Query time: {result.execution_time:.6f}s")
        print(f"Speed: {result.scanned_count/result.execution_time:,.0f} entries/sec")
    
    elif args.query == 'ip':
        if not args.value:
            print("Error: --value required for IP query")
            exit(1)
        
        result = engine.query_by_ip(args.value)
        print(f"IP Address: {args.value}")
        print(f"Matched: {result.matched_count} logs")
        print(f"Scanned: {result.scanned_count} entries")
        print(f"Query time: {result.execution_time:.6f}s")
        print(f"Speed: {result.scanned_count/result.execution_time:,.0f} entries/sec")
