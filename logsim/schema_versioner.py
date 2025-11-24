#!/usr/bin/env python3
"""
Schema versioning and evolution tracking

Tracks how log schemas change over time:
- Detects schema drift when new fields appear
- Maintains version history (v1, v2, v3)
- Provides compatibility matrix for queries
"""

import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Set
from pathlib import Path
from datetime import datetime
import hashlib


@dataclass
class SchemaVersion:
    """A version of a log schema"""
    version: int
    timestamp: str
    template: str
    fields: List[str]
    field_types: Dict[str, str]
    sample_count: int
    template_hash: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict) -> 'SchemaVersion':
        """Create from dictionary"""
        return SchemaVersion(**data)


@dataclass
class SchemaEvolution:
    """Evolution history of a log source"""
    source_name: str
    versions: List[SchemaVersion]
    current_version: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'source_name': self.source_name,
            'versions': [v.to_dict() for v in self.versions],
            'current_version': self.current_version
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'SchemaEvolution':
        """Create from dictionary"""
        return SchemaEvolution(
            source_name=data['source_name'],
            versions=[SchemaVersion.from_dict(v) for v in data['versions']],
            current_version=data['current_version']
        )


class SchemaVersioner:
    """Track and manage schema evolution"""
    
    def __init__(self, storage_dir: Path = Path("schema_versions")):
        """
        Initialize schema versioner
        
        Args:
            storage_dir: Directory to store schema version history
        """
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(exist_ok=True)
        self.evolutions: Dict[str, SchemaEvolution] = {}
    
    def _compute_template_hash(self, template: str, fields: List[str]) -> str:
        """Compute hash of template structure"""
        content = f"{template}|{'|'.join(sorted(fields))}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def register_schema(
        self,
        source_name: str,
        template: str,
        fields: List[str],
        field_types: Dict[str, str],
        sample_count: int
    ) -> int:
        """
        Register a new schema or update existing
        
        Args:
            source_name: Name of log source (e.g., "Apache", "Zookeeper")
            template: Template pattern
            fields: List of field names
            field_types: Mapping of field names to semantic types
            sample_count: Number of logs this schema applies to
        
        Returns:
            Version number (incremented if schema changed)
        """
        template_hash = self._compute_template_hash(template, fields)
        
        # Load existing evolution if available
        if source_name not in self.evolutions:
            self.evolutions[source_name] = self._load_evolution(source_name)
        
        evolution = self.evolutions[source_name]
        
        # Check if schema changed
        if evolution.versions:
            current = evolution.versions[-1]
            if current.template_hash == template_hash:
                # Schema unchanged, update sample count
                current.sample_count += sample_count
                self._save_evolution(evolution)
                return current.version
        
        # New schema version
        new_version = len(evolution.versions) + 1
        schema_version = SchemaVersion(
            version=new_version,
            timestamp=datetime.now().isoformat(),
            template=template,
            fields=fields,
            field_types=field_types,
            sample_count=sample_count,
            template_hash=template_hash
        )
        
        evolution.versions.append(schema_version)
        evolution.current_version = new_version
        
        self._save_evolution(evolution)
        
        print(f"📝 Registered schema version {new_version} for {source_name}")
        if new_version > 1:
            print(f"   ⚠️  Schema evolved from v{new_version-1} to v{new_version}")
        
        return new_version
    
    def get_version(self, source_name: str, version: int) -> Optional[SchemaVersion]:
        """Get a specific schema version"""
        if source_name not in self.evolutions:
            self.evolutions[source_name] = self._load_evolution(source_name)
        
        evolution = self.evolutions[source_name]
        for v in evolution.versions:
            if v.version == version:
                return v
        return None
    
    def get_current_version(self, source_name: str) -> Optional[SchemaVersion]:
        """Get the current (latest) schema version"""
        if source_name not in self.evolutions:
            self.evolutions[source_name] = self._load_evolution(source_name)
        
        evolution = self.evolutions[source_name]
        if evolution.versions:
            return evolution.versions[-1]
        return None
    
    def get_evolution_history(self, source_name: str) -> List[SchemaVersion]:
        """Get full evolution history for a source"""
        if source_name not in self.evolutions:
            self.evolutions[source_name] = self._load_evolution(source_name)
        
        return self.evolutions[source_name].versions
    
    def compare_versions(
        self,
        source_name: str,
        version1: int,
        version2: int
    ) -> Dict[str, any]:
        """
        Compare two schema versions
        
        Returns:
            Dictionary with:
            - added_fields: Fields added in version2
            - removed_fields: Fields removed in version2
            - changed_types: Fields with different types
            - compatible: Whether versions are query-compatible
        """
        v1 = self.get_version(source_name, version1)
        v2 = self.get_version(source_name, version2)
        
        if not v1 or not v2:
            return {
                'error': 'Version not found',
                'compatible': False
            }
        
        fields1 = set(v1.fields)
        fields2 = set(v2.fields)
        
        added = fields2 - fields1
        removed = fields1 - fields2
        common = fields1 & fields2
        
        changed_types = {}
        for field in common:
            type1 = v1.field_types.get(field)
            type2 = v2.field_types.get(field)
            if type1 != type2:
                changed_types[field] = {'from': type1, 'to': type2}
        
        # Compatible if no fields removed and no type changes
        compatible = len(removed) == 0 and len(changed_types) == 0
        
        return {
            'added_fields': list(added),
            'removed_fields': list(removed),
            'changed_types': changed_types,
            'compatible': compatible,
            'compatibility_level': self._compute_compatibility(removed, changed_types)
        }
    
    def _compute_compatibility(
        self,
        removed: Set[str],
        changed_types: Dict[str, Dict]
    ) -> str:
        """Compute compatibility level"""
        if not removed and not changed_types:
            return 'BACKWARD_COMPATIBLE'  # v2 adds fields only
        elif not removed:
            return 'COMPATIBLE_WITH_CAST'  # Type changes need casting
        else:
            return 'INCOMPATIBLE'  # Queries may fail
    
    def get_compatibility_matrix(self, source_name: str) -> Dict[str, Dict[str, str]]:
        """
        Generate compatibility matrix for all versions
        
        Returns:
            Matrix where result[v1][v2] = compatibility level
        """
        versions = self.get_evolution_history(source_name)
        matrix = {}
        
        for v1 in versions:
            matrix[f"v{v1.version}"] = {}
            for v2 in versions:
                if v1.version == v2.version:
                    matrix[f"v{v1.version}"][f"v{v2.version}"] = 'IDENTICAL'
                else:
                    comparison = self.compare_versions(
                        source_name,
                        v1.version,
                        v2.version
                    )
                    matrix[f"v{v1.version}"][f"v{v2.version}"] = comparison['compatibility_level']
        
        return matrix
    
    def _load_evolution(self, source_name: str) -> SchemaEvolution:
        """Load evolution history from disk"""
        filepath = self.storage_dir / f"{source_name}.json"
        
        if filepath.exists():
            with open(filepath, 'r') as f:
                data = json.load(f)
                return SchemaEvolution.from_dict(data)
        
        # Create new evolution
        return SchemaEvolution(
            source_name=source_name,
            versions=[],
            current_version=0
        )
    
    def _save_evolution(self, evolution: SchemaEvolution):
        """Save evolution history to disk"""
        filepath = self.storage_dir / f"{evolution.source_name}.json"
        
        with open(filepath, 'w') as f:
            json.dump(evolution.to_dict(), f, indent=2)
    
    def print_evolution_summary(self, source_name: str):
        """Print evolution summary for a source"""
        versions = self.get_evolution_history(source_name)
        
        if not versions:
            print(f"No schema versions found for {source_name}")
            return
        
        print(f"\n📊 Schema Evolution: {source_name}")
        print("=" * 80)
        
        for v in versions:
            print(f"\nVersion {v.version} (registered: {v.timestamp})")
            print(f"  Template: {v.template}")
            print(f"  Fields: {', '.join(v.fields)}")
            print(f"  Sample count: {v.sample_count:,} logs")
            
            if v.version > 1:
                prev = versions[v.version - 2]
                comparison = self.compare_versions(source_name, prev.version, v.version)
                
                if comparison['added_fields']:
                    print(f"  ➕ Added: {', '.join(comparison['added_fields'])}")
                if comparison['removed_fields']:
                    print(f"  ➖ Removed: {', '.join(comparison['removed_fields'])}")
                if comparison['changed_types']:
                    print(f"  🔄 Changed types: {len(comparison['changed_types'])} fields")
                
                print(f"  ✓ Compatibility: {comparison['compatibility_level']}")


def main():
    """Demo schema versioning"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Schema version management")
    parser.add_argument('--source', required=True, help='Log source name')
    parser.add_argument('--action', choices=['show', 'matrix'], default='show')
    
    args = parser.parse_args()
    
    versioner = SchemaVersioner()
    
    if args.action == 'show':
        versioner.print_evolution_summary(args.source)
    elif args.action == 'matrix':
        matrix = versioner.get_compatibility_matrix(args.source)
        
        print(f"\n📊 Compatibility Matrix: {args.source}")
        print("=" * 80)
        
        versions = list(matrix.keys())
        if versions:
            # Print header
            print(f"{'':8}", end='')
            for v in versions:
                print(f"{v:20}", end='')
            print()
            
            # Print rows
            for v1 in versions:
                print(f"{v1:8}", end='')
                for v2 in versions:
                    compat = matrix[v1][v2]
                    if compat == 'IDENTICAL':
                        symbol = '='
                    elif compat == 'BACKWARD_COMPATIBLE':
                        symbol = '✓'
                    elif compat == 'COMPATIBLE_WITH_CAST':
                        symbol = '~'
                    else:
                        symbol = '✗'
                    print(f"{symbol:20}", end='')
                print()
            
            print("\nLegend:")
            print("  = : Identical schemas")
            print("  ✓ : Backward compatible (fields added)")
            print("  ~ : Compatible with type casting")
            print("  ✗ : Incompatible (fields removed)")


if __name__ == "__main__":
    main()
