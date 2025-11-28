"""
CLI commands for LogSim.
"""

import click
import sys
from pathlib import Path
from logsim.services import SemanticCompressor

@click.command()
@click.option('--input', '-i', required=True, help='Input log file path')
@click.option('--output', '-o', required=True, help='Output compressed file path')
@click.option('--measure', '-m', is_flag=True, help='Measure and display compression metrics')
@click.option('--min-support', default=3, help='Minimum support for template extraction (default: 3)')
def compress(input, output, measure, min_support):
    """
    Compress log files using semantic schema extraction.
    
    Example:
        logsim compress -i datasets/Apache/Apache_full.log -o compressed/apache.lsc -m
    """
    import time
    input_path = Path(input)
    output_path = Path(output)
    
    if not input_path.exists():
        click.echo(f"Error: Input file not found: {input}", err=True)
        sys.exit(1)
    
    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    click.echo(f"Compressing {input_path.name}...")
    
    compressor = SemanticCompressor(min_support=min_support)
    
    # Read logs
    with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
        logs = [line.strip() for line in f if line.strip()]
    
    click.echo(f"Processing {len(logs)} log entries...")
    
    # Compress with timing
    start = time.time()
    compressed_log, stats = compressor.compress(logs, verbose=False)
    elapsed = time.time() - start
    
    # Save to file
    compressor.save(output_path, verbose=False)
    
    if measure:
        original_size = input_path.stat().st_size
        compressed_size = output_path.stat().st_size
        ratio = original_size / compressed_size if compressed_size > 0 else 0
        
        click.echo("\n=== Compression Results ===")
        click.echo(f"Original size: {original_size / 1024 / 1024:.2f} MB")
        click.echo(f"Compressed size: {compressed_size / 1024 / 1024:.2f} MB")
        click.echo(f"Compression ratio: {ratio:.2f}×")
        click.echo(f"Templates extracted: {stats.template_count}")
        click.echo(f"Processing time: {elapsed:.2f}s")
    
    click.echo(f"\n✓ Compressed to {output_path}")


@click.command()
@click.option('--compressed', '-c', required=True, help='Compressed file path')
@click.option('--severity', help='Filter by severity (ERROR, WARN, INFO)')
@click.option('--ip', help='Filter by IP address')
@click.option('--limit', type=int, default=10, help='Max results to display (default: 10)')
def query(compressed, severity, ip, limit):
    """
    Query compressed log files without full decompression.
    
    Example:
        logsim query -c compressed/apache.lsc --severity ERROR --limit 20
    """
    from logsim.services import QueryEngine

    compressed_path = Path(compressed)
    if not compressed_path.exists():
        click.echo(f"Error: Compressed file not found: {compressed}", err=True)
        sys.exit(1)

    # Use QueryEngine service (it provides QueryResult objects)
    engine = QueryEngine(str(compressed_path))

    # Show total logs
    try:
        total = engine.count_all().matched_count
    except Exception:
        total = engine.compressed.original_count if engine.compressed else 0

    click.echo(f"Total logs: {total}")

    if severity:
        click.echo(f"\nQuerying for severity={severity}...")
        qr = engine.query_by_severity([severity])
    elif ip:
        click.echo(f"\nQuerying for IP={ip}...")
        qr = engine.query_by_ip(ip)
    else:
        click.echo("Error: Specify --severity or --ip filter", err=True)
        sys.exit(1)

    # Present results
    click.echo(f"\nMatched: {qr.matched_count} rows (execution: {qr.execution_time:.4f}s)")
    if qr.matched_logs:
        click.echo(f"\nShowing up to {limit} results:\n")
        for log in qr.matched_logs[:limit]:
            click.echo(log)
    elif qr.matched_count > 0:
        click.echo("\nNote: Matched logs found but reconstruction took too long. Try reducing result set.")
    else:
        click.echo("\nNo matching logs found.")


if __name__ == '__main__':
    compress()
