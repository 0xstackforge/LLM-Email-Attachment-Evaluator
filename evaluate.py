import json
from pathlib import Path
from typing import Dict, List, Tuple


def load_json_file(file_path: Path) -> Dict[str, List[str]]:
    with open(file_path, 'r') as f:
        return json.load(f)


def evaluate_classification(predicted: Dict[str, List[str]], 
                           ground_truth: Dict[str, List[str]]) -> Dict[str, float]:
    # Get sets of attachments
    pred_relevant = set(predicted.get("relevant", []))
    pred_irrelevant = set(predicted.get("irrelevant", []))
    gt_relevant = set(ground_truth.get("relevant", []))
    gt_irrelevant = set(ground_truth.get("irrelevant", []))
    
    # All attachments
    pred_all = pred_relevant | pred_irrelevant
    gt_all = gt_relevant | gt_irrelevant
    
    # Calculate metrics
    # True Positives: correctly classified as relevant
    tp = len(pred_relevant & gt_relevant)
    
    # True Negatives: correctly classified as irrelevant
    tn = len(pred_irrelevant & gt_irrelevant)
    
    # False Positives: predicted relevant but actually irrelevant
    fp = len(pred_relevant & gt_irrelevant)
    
    # False Negatives: predicted irrelevant but actually relevant
    fn = len(pred_irrelevant & gt_relevant)
    
    # Accuracy
    total = tp + tn + fp + fn
    accuracy = (tp + tn) / total if total > 0 else 0.0
    
    # Precision (for relevant class)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    
    # Recall (for relevant class)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    
    # F1 Score
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    # Missing attachments (in ground truth but not in prediction)
    missing = gt_all - pred_all
    
    # Extra attachments (in prediction but not in ground truth)
    extra = pred_all - gt_all
    
    return {
        "true_positives": tp,
        "true_negatives": tn,
        "false_positives": fp,
        "false_negatives": fn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "missing_attachments": sorted(list(missing)),
        "extra_attachments": sorted(list(extra))
    }


def main():
    output_dir = Path("output")
    ground_truth_dir = Path("ground_truth")
    
    if not output_dir.exists():
        print(f"Error: Output directory {output_dir} does not exist")
        return
    
    if not ground_truth_dir.exists():
        print(f"Error: Ground truth directory {ground_truth_dir} does not exist")
        return
    
    # Find all ground truth files
    gt_files = sorted(ground_truth_dir.glob("*.json"))
    
    if not gt_files:
        print(f"No ground truth files found in {ground_truth_dir}")
        return
    
    print(f"Found {len(gt_files)} ground truth files\n")
    
    all_metrics = []
    
    for gt_file in gt_files:
        # Extract example number
        match = gt_file.stem.replace("attachments_", "")
        example_num = match
        
        output_file = output_dir / f"attachments_{example_num}.json"
        
        if not output_file.exists():
            print(f"⚠ {gt_file.name}: No corresponding output file found")
            continue
        
        try:
            # Load files
            ground_truth = load_json_file(gt_file)
            predicted = load_json_file(output_file)
            
            # Evaluate
            metrics = evaluate_classification(predicted, ground_truth)
            all_metrics.append(metrics)
            
            # Print results
            print(f"📊 {gt_file.name}:")
            print(f"   Accuracy:  {metrics['accuracy']:.4f}")
            print(f"   Precision: {metrics['precision']:.4f}")
            print(f"   Recall:    {metrics['recall']:.4f}")
            print(f"   F1 Score:  {metrics['f1_score']:.4f}")
            print(f"   TP: {metrics['true_positives']}, TN: {metrics['true_negatives']}, "
                  f"FP: {metrics['false_positives']}, FN: {metrics['false_negatives']}")
            
            if metrics['missing_attachments']:
                print(f"   ⚠ Missing: {metrics['missing_attachments']}")
            if metrics['extra_attachments']:
                print(f"   ⚠ Extra: {metrics['extra_attachments']}")
            print()
            
        except Exception as e:
            print(f"❌ Error evaluating {gt_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Calculate overall metrics
    if all_metrics:
        print("=" * 60)
        print("OVERALL METRICS:")
        print("=" * 60)
        
        total_tp = sum(m['true_positives'] for m in all_metrics)
        total_tn = sum(m['true_negatives'] for m in all_metrics)
        total_fp = sum(m['false_positives'] for m in all_metrics)
        total_fn = sum(m['false_negatives'] for m in all_metrics)
        
        overall_accuracy = (total_tp + total_tn) / (total_tp + total_tn + total_fp + total_fn) if (total_tp + total_tn + total_fp + total_fn) > 0 else 0.0
        overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        overall_f1 = 2 * (overall_precision * overall_recall) / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0.0
        
        print(f"Accuracy:  {overall_accuracy:.4f}")
        print(f"Precision: {overall_precision:.4f}")
        print(f"Recall:    {overall_recall:.4f}")
        print(f"F1 Score:  {overall_f1:.4f}")
        print(f"\nTotal - TP: {total_tp}, TN: {total_tn}, FP: {total_fp}, FN: {total_fn}")


if __name__ == "__main__":
    main()
