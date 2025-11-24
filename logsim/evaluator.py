#!/usr/bin/env python3
"""
Evaluation framework for schema extraction accuracy

Calculates precision, recall, and F1-score by comparing extracted schemas
against manually annotated ground truth.
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, asdict
import argparse


@dataclass
class FieldAnnotation:
    """Ground truth annotation for a field"""
    name: str
    type: str
    start_pos: int
    end_pos: int
    value: str


@dataclass
class LogAnnotation:
    """Ground truth annotation for a single log"""
    log_id: str
    raw_text: str
    fields: List[FieldAnnotation]
    
    def to_dict(self) -> Dict:
        return {
            'log_id': self.log_id,
            'raw_text': self.raw_text,
            'fields': [asdict(f) for f in self.fields]
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'LogAnnotation':
        return LogAnnotation(
            log_id=data['log_id'],
            raw_text=data['raw_text'],
            fields=[FieldAnnotation(**f) for f in data['fields']]
        )


@dataclass
class EvaluationMetrics:
    """Evaluation metrics"""
    precision: float
    recall: float
    f1_score: float
    true_positives: int
    false_positives: int
    false_negatives: int
    total_ground_truth: int
    total_extracted: int
    
    def to_dict(self) -> Dict:
        return asdict(self)


class SchemaEvaluator:
    """Evaluate schema extraction accuracy"""
    
    def __init__(self):
        """Initialize evaluator"""
        self.ground_truth: Dict[str, LogAnnotation] = {}
        self.extracted_schemas: Dict[str, List[Dict]] = {}
    
    def load_ground_truth(self, filepath: Path):
        """
        Load ground truth annotations
        
        Expected format:
        {
          "annotations": [
            {
              "log_id": "apache_001",
              "raw_text": "[Thu Jun 09 06:07:04 2005] [notice] LDAP: Built with OpenLDAP",
              "fields": [
                {"name": "timestamp", "type": "TIMESTAMP", "start_pos": 1, "end_pos": 25, "value": "Thu Jun 09 06:07:04 2005"},
                {"name": "severity", "type": "SEVERITY", "start_pos": 28, "end_pos": 34, "value": "notice"},
                {"name": "message", "type": "MESSAGE", "start_pos": 36, "end_pos": 64, "value": "LDAP: Built with OpenLDAP"}
              ]
            }
          ]
        }
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        for annotation_data in data['annotations']:
            annotation = LogAnnotation.from_dict(annotation_data)
            self.ground_truth[annotation.log_id] = annotation
        
        print(f"✓ Loaded {len(self.ground_truth)} ground truth annotations")
    
    def load_extracted_schemas(self, filepath: Path):
        """
        Load extracted schemas from template_generator output
        
        Expected format:
        {
          "templates": [
            {
              "template_id": "T001",
              "pattern": "[TIMESTAMP] [SEVERITY] MESSAGE",
              "fields": ["TIMESTAMP", "SEVERITY", "MESSAGE"],
              "examples": [...]
            }
          ]
        }
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Store templates for matching
        self.extracted_schemas = data
        
        print(f"✓ Loaded {len(data.get('templates', []))} extracted templates")
    
    def extract_fields_from_template(
        self,
        log_text: str,
        template_pattern: str,
        field_types: List[str]
    ) -> List[FieldAnnotation]:
        """
        Extract field positions from log text using template pattern
        
        This is a simplified version - in practice, you'd use the tokenizer
        and semantic type recognizer to match fields.
        """
        fields = []
        
        # For now, return empty list - this would need full integration
        # with the tokenizer to properly extract field boundaries
        
        return fields
    
    def evaluate_field_extraction(self, log_id: str) -> Tuple[int, int, int]:
        """
        Evaluate field extraction for a single log
        
        Returns:
            (true_positives, false_positives, false_negatives)
        """
        if log_id not in self.ground_truth:
            return 0, 0, 0
        
        ground_truth = self.ground_truth[log_id]
        
        # Get ground truth fields
        gt_fields = {f.type for f in ground_truth.fields}
        
        # For demo purposes, we'll need to match extracted fields
        # In practice, this would use the actual extraction results
        extracted_fields = set()  # Placeholder
        
        # Calculate metrics
        true_positives = len(gt_fields & extracted_fields)
        false_positives = len(extracted_fields - gt_fields)
        false_negatives = len(gt_fields - extracted_fields)
        
        return true_positives, false_positives, false_negatives
    
    def evaluate_all(self) -> EvaluationMetrics:
        """
        Evaluate extraction accuracy across all annotated logs
        
        Returns:
            Overall metrics (precision, recall, F1)
        """
        total_tp = 0
        total_fp = 0
        total_fn = 0
        
        for log_id in self.ground_truth:
            tp, fp, fn = self.evaluate_field_extraction(log_id)
            total_tp += tp
            total_fp += fp
            total_fn += fn
        
        # Calculate metrics
        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return EvaluationMetrics(
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            true_positives=total_tp,
            false_positives=total_fp,
            false_negatives=total_fn,
            total_ground_truth=total_tp + total_fn,
            total_extracted=total_tp + total_fp
        )
    
    def print_metrics(self, metrics: EvaluationMetrics):
        """Print evaluation metrics"""
        print("\n" + "="*80)
        print("📊 Schema Extraction Evaluation Metrics")
        print("="*80)
        
        print(f"\n✅ True Positives:  {metrics.true_positives:4d}  (correctly extracted fields)")
        print(f"❌ False Positives: {metrics.false_positives:4d}  (incorrectly extracted fields)")
        print(f"❌ False Negatives: {metrics.false_negatives:4d}  (missed fields)")
        
        print(f"\n📈 Overall Metrics:")
        print(f"  • Precision: {metrics.precision*100:6.2f}%  (of extracted fields, how many are correct)")
        print(f"  • Recall:    {metrics.recall*100:6.2f}%  (of ground truth fields, how many were found)")
        print(f"  • F1-Score:  {metrics.f1_score*100:6.2f}%  (harmonic mean of precision and recall)")
        
        print(f"\n📊 Dataset Summary:")
        print(f"  • Ground truth fields: {metrics.total_ground_truth}")
        print(f"  • Extracted fields:    {metrics.total_extracted}")
        print(f"  • Annotated logs:      {len(self.ground_truth)}")
        
        # Interpretation
        print(f"\n💡 Interpretation:")
        if metrics.f1_score >= 0.90:
            print("  ✅ Excellent accuracy (≥90%) - meets thesis target")
        elif metrics.f1_score >= 0.80:
            print("  ✓ Good accuracy (80-90%) - room for improvement")
        elif metrics.f1_score >= 0.70:
            print("  ⚠ Moderate accuracy (70-80%) - needs optimization")
        else:
            print("  ❌ Low accuracy (<70%) - significant improvements needed")
        
        print("="*80)


def create_sample_ground_truth(output_path: Path):
    """Create sample ground truth annotations for demonstration"""
    
    annotations = {
        'dataset': 'Apache',
        'created_at': '2025-11-23',
        'annotations': [
            {
                'log_id': 'apache_001',
                'raw_text': '[Thu Jun 09 06:07:04 2005] [notice] LDAP: Built with OpenLDAP LDAP SDK',
                'fields': [
                    {
                        'name': 'timestamp',
                        'type': 'TIMESTAMP',
                        'start_pos': 1,
                        'end_pos': 25,
                        'value': 'Thu Jun 09 06:07:04 2005'
                    },
                    {
                        'name': 'severity',
                        'type': 'SEVERITY',
                        'start_pos': 28,
                        'end_pos': 34,
                        'value': 'notice'
                    },
                    {
                        'name': 'message',
                        'type': 'MESSAGE',
                        'start_pos': 36,
                        'end_pos': 71,
                        'value': 'LDAP: Built with OpenLDAP LDAP SDK'
                    }
                ]
            },
            {
                'log_id': 'apache_002',
                'raw_text': '[Thu Jun 09 06:07:04 2005] [notice] LDAP: SSL support unavailable',
                'fields': [
                    {
                        'name': 'timestamp',
                        'type': 'TIMESTAMP',
                        'start_pos': 1,
                        'end_pos': 25,
                        'value': 'Thu Jun 09 06:07:04 2005'
                    },
                    {
                        'name': 'severity',
                        'type': 'SEVERITY',
                        'start_pos': 28,
                        'end_pos': 34,
                        'value': 'notice'
                    },
                    {
                        'name': 'message',
                        'type': 'MESSAGE',
                        'start_pos': 36,
                        'end_pos': 64,
                        'value': 'LDAP: SSL support unavailable'
                    }
                ]
            }
        ]
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(annotations, f, indent=2)
    
    print(f"✓ Created sample ground truth: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate schema extraction accuracy")
    parser.add_argument('--ground-truth', type=Path, help='Path to ground truth annotations')
    parser.add_argument('--extracted', type=Path, help='Path to extracted schemas')
    parser.add_argument('--create-sample', action='store_true', help='Create sample ground truth')
    parser.add_argument('--output', type=Path, default=Path('ground_truth_sample.json'))
    
    args = parser.parse_args()
    
    if args.create_sample:
        create_sample_ground_truth(args.output)
        return
    
    if not args.ground_truth or not args.extracted:
        print("Usage: python evaluator.py --ground-truth GT.json --extracted SCHEMAS.json")
        print("   or: python evaluator.py --create-sample --output sample.json")
        return
    
    evaluator = SchemaEvaluator()
    evaluator.load_ground_truth(args.ground_truth)
    evaluator.load_extracted_schemas(args.extracted)
    
    metrics = evaluator.evaluate_all()
    evaluator.print_metrics(metrics)
    
    # Save metrics to file
    output_path = args.extracted.parent / 'evaluation_metrics.json'
    with open(output_path, 'w') as f:
        json.dump(metrics.to_dict(), f, indent=2)
    print(f"\n💾 Metrics saved to: {output_path}")


if __name__ == "__main__":
    main()
