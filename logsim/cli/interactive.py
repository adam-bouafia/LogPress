#!/usr/bin/env python3
"""
Interactive CLI menu for LogSim using rich library
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.tree import Tree
from rich.layout import Layout
from rich import box
from pathlib import Path
import time
from typing import List, Dict, Optional
from dataclasses import dataclass

# Import LogSim components
from logsim.services.compressor import SemanticCompressor

console = Console()


@dataclass
class Dataset:
    """Dataset information"""
    name: str
    path: Path
    lines: int
    size_mb: float


class InteractiveCLI:
    """Interactive CLI for LogSim with rich UI"""
    
    def __init__(self):
        self.data_dir = Path("data/datasets")
        self.compressed_dir = Path("evaluation/compressed")
        self.results_dir = Path("evaluation/results")
        self.datasets: List[Dataset] = []
        self.settings = {
            'min_support': 3,
            'zstd_level': 15,
            'measure': True,
            'enable_bwt': True,
        }
    
    def scan_datasets(self) -> List[Dataset]:
        """Scan data/datasets/ for available log files"""
        datasets = []
        
        if not self.data_dir.exists():
            console.print(f"[red]Error: {self.data_dir} not found![/red]")
            return datasets
        
        with console.status("[cyan]Scanning datasets...[/cyan]"):
            for dataset_dir in self.data_dir.iterdir():
                if dataset_dir.is_dir():
                    log_file = None
                    
                    # Try multiple naming patterns
                    patterns = [
                        dataset_dir / f"{dataset_dir.name}_full.log",  # Apache_full.log
                        dataset_dir / f"{dataset_dir.name}.log",        # BGL.log
                        dataset_dir / f"{dataset_dir.name.lower()}.log" # openstack.log
                    ]
                    
                    for pattern in patterns:
                        if pattern.exists():
                            log_file = pattern
                            break
                    
                    if log_file and log_file.exists():
                        try:
                            lines = sum(1 for _ in open(log_file, 'r', errors='ignore'))
                            size_mb = log_file.stat().st_size / (1024 * 1024)
                            
                            datasets.append(Dataset(
                                name=dataset_dir.name,
                                path=log_file,
                                lines=lines,
                                size_mb=size_mb
                            ))
                        except Exception as e:
                            console.print(f"[yellow]Warning: Could not read {log_file}: {e}[/yellow]")
        
        return sorted(datasets, key=lambda x: x.name)
    
    def show_main_menu(self):
        """Display main menu with dataset listing"""
        console.clear()
        
        # Header
        console.print(Panel.fit(
            "[bold cyan]LogSim - Log Compression System[/bold cyan]\n"
            "[dim]Semantic-Aware Compression & Schema Extraction[/dim]",
            border_style="purple",
            box=box.DOUBLE
        ))
        console.print()
        
        # Dataset table
        if self.datasets:
            table = Table(
                title="📁 Detected Datasets",
                show_header=True,
                header_style="bold green",
                box=box.ROUNDED
            )
            table.add_column("#", style="yellow", width=4, justify="right")
            table.add_column("Dataset", style="cyan")
            table.add_column("Lines", justify="right", style="green")
            table.add_column("Size", justify="right", style="blue")
            
            for i, ds in enumerate(self.datasets, 1):
                table.add_row(
                    str(i),
                    ds.name,
                    f"{ds.lines:,}",
                    f"{ds.size_mb:.2f} MB"
                )
            
            console.print(table)
        else:
            console.print("[red]No datasets found in data/datasets/[/red]")
        
        console.print()
        
        # Actions menu
        actions_table = Table(show_header=False, box=None, padding=(0, 2))
        actions_table.add_column("Key", style="yellow")
        actions_table.add_column("Action", style="white")
        
        actions_table.add_row("[1]", "🗜️  Compress selected datasets")
        actions_table.add_row("[2]", "🔍 Query compressed files")
        actions_table.add_row("[3]", "📊 Run full evaluation")
        actions_table.add_row("[4]", "⚖️  Benchmark comparison (vs gzip)")
        actions_table.add_row("[5]", "📈 View results")
        actions_table.add_row("[6]", "⚙️  Settings")
        actions_table.add_row("[0]", "🚪 Exit")
        
        console.print(Panel(actions_table, title="[bold green]🎬 Actions[/bold green]", border_style="green"))
        console.print()
        
        choice = Prompt.ask("Select option", default="1")
        self.handle_menu_choice(choice)
    
    def handle_menu_choice(self, choice: str):
        """Handle main menu selection"""
        try:
            if choice == "1":
                self.compress_datasets()
            elif choice == "2":
                self.query_files()
            elif choice == "3":
                self.run_evaluation()
            elif choice == "4":
                self.benchmark_comparison()
            elif choice == "5":
                self.view_results()
            elif choice == "6":
                self.settings_menu()
            elif choice == "0" or choice.lower() == "x":
                console.print("[yellow]Exiting...[/yellow]")
                exit(0)
            else:
                console.print("[red]Invalid option![/red]")
                time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled[/yellow]")
            time.sleep(1)
    
    def compress_datasets(self):
        """Interactive dataset compression"""
        console.clear()
        console.print(Panel("Compress Datasets", style="cyan", box=box.DOUBLE))
        console.print()
        
        if not self.datasets:
            console.print("[red]No datasets available![/red]")
            Prompt.ask("Press enter to continue")
            return
        
        # Dataset selection
        console.print("[green]Select datasets to compress:[/green]")
        console.print("[dim]Examples: '1,3,5' for specific datasets | '1-5' for range | 'all' for all datasets[/dim]")
        console.print()
        
        # Show numbered list
        for i, ds in enumerate(self.datasets, 1):
            console.print(f"  [{i}] {ds.name} - {ds.lines:,} lines ({ds.size_mb:.2f} MB)")
        
        console.print()
        selection = Prompt.ask("Select datasets", default="all")
        
        selected = []
        if selection.lower() == "all":
            selected = self.datasets[:]
            console.print(f"[green]✓ All {len(selected)} datasets selected[/green]")
        else:
            try:
                indices = []
                # Parse input: support both "1,3,5" and "1-5" ranges
                for part in selection.split(','):
                    part = part.strip()
                    if '-' in part:
                        # Handle range like "1-5"
                        start, end = part.split('-', 1)
                        indices.extend(range(int(start.strip()), int(end.strip()) + 1))
                    else:
                        # Handle single number
                        indices.append(int(part))
                
                # Remove duplicates and sort
                indices = sorted(set(indices))
                
                for idx in indices:
                    if 1 <= idx <= len(self.datasets):
                        selected.append(self.datasets[idx - 1])
                        console.print(f"[green]✓[/green] {self.datasets[idx - 1].name} selected")
                    else:
                        console.print(f"[yellow]⚠[/yellow] Invalid index: {idx}")
            except (ValueError, AttributeError) as e:
                console.print(f"[red]Invalid input format! Use: 1,3,5 or 1-5 or all[/red]")
                Prompt.ask("Press enter to continue")
                return
        
        if not selected:
            console.print("[red]No datasets selected![/red]")
            Prompt.ask("Press enter to continue")
            return
        
        # Settings
        console.print()
        console.print("[yellow]⚙️  Compression Settings:[/yellow]")
        console.print("[dim]Min support: Minimum times a pattern must appear to become a template (higher = fewer templates)[/dim]")
        min_support = IntPrompt.ask(
            "  Min support",
            default=self.settings['min_support']
        )
        measure = Confirm.ask("  Measure metrics?", default=True)
        
        console.print()
        
        # Create output directory
        self.compressed_dir.mkdir(parents=True, exist_ok=True)
        
        # Compress with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(complete_style="green", finished_style="bold green"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            overall_task = progress.add_task(
                "[cyan]Overall progress",
                total=len(selected)
            )
            
            results = []
            
            for ds in selected:
                # Add task for this dataset
                task = progress.add_task(
                    f"[green]Compressing {ds.name}",
                    total=100
                )
                
                try:
                    # Read logs
                    progress.update(task, description=f"[yellow]Reading {ds.name}")
                    with open(ds.path, 'r', errors='ignore') as f:
                        logs = [line.strip() for line in f if line.strip()]
                    progress.update(task, advance=20)
                    
                    # Compress
                    progress.update(task, description=f"[cyan]Compressing {ds.name}")
                    compressor = SemanticCompressor(min_support=min_support)
                    compressed_log, stats = compressor.compress(logs, verbose=False)
                    progress.update(task, advance=60)
                    
                    # Save
                    progress.update(task, description=f"[blue]Saving {ds.name}")
                    output = self.compressed_dir / f"{ds.name.lower()}_full.lsc"
                    compressor.save(output, verbose=False)
                    progress.update(task, advance=20)
                    
                    # Calculate metrics
                    if measure:
                        compressed_size = output.stat().st_size
                        ratio = (ds.size_mb * 1024 * 1024) / compressed_size
                        results.append({
                            'name': ds.name,
                            'ratio': ratio,
                            'templates': stats.template_count,
                            'original_mb': ds.size_mb,
                            'compressed_kb': compressed_size / 1024
                        })
                    
                    progress.update(overall_task, advance=1)
                    progress.update(task, description=f"[green]✓ {ds.name} complete")
                    
                except Exception as e:
                    progress.update(task, description=f"[red]✗ {ds.name} failed: {e}")
                    console.print(f"[red]Error compressing {ds.name}: {e}[/red]")
        
        console.print()
        
        # Display results
        if results:
            results_table = Table(title="Compression Results", box=box.ROUNDED)
            results_table.add_column("Dataset", style="cyan")
            results_table.add_column("Ratio", justify="right", style="green")
            results_table.add_column("Templates", justify="right", style="yellow")
            results_table.add_column("Original", justify="right", style="blue")
            results_table.add_column("Compressed", justify="right", style="magenta")
            
            for r in results:
                results_table.add_row(
                    r['name'],
                    f"{r['ratio']:.2f}×",
                    str(r['templates']),
                    f"{r['original_mb']:.2f} MB",
                    f"{r['compressed_kb']:.2f} KB"
                )
            
            console.print(results_table)
        
        console.print()
        console.print("[green]✓ Compression complete![/green]")
        Prompt.ask("Press enter to continue")
    
    def query_files(self):
        """Query compressed files"""
        console.clear()
        console.print(Panel("Query Compressed Logs", style="cyan", box=box.DOUBLE))
        console.print()
        
        if not self.compressed_dir.exists():
            console.print("[red]No compressed files found![/red]")
            Prompt.ask("Press enter to continue")
            return
        
        # List compressed files
        compressed_files = list(self.compressed_dir.glob("*.lsc"))
        
        if not compressed_files:
            console.print("[red]No compressed files found![/red]")
            Prompt.ask("Press enter to continue")
            return
        
        table = Table(title="📦 Available Compressed Files", box=box.ROUNDED)
        table.add_column("#", style="yellow", width=4)
        table.add_column("File", style="cyan")
        table.add_column("Size", justify="right", style="blue")
        
        for i, file in enumerate(compressed_files, 1):
            size_kb = file.stat().st_size / 1024
            table.add_row(str(i), file.stem, f"{size_kb:.2f} KB")
        
        console.print(table)
        console.print()
        
        choice = Prompt.ask("Select file number (or 'b' for back)", default="b")
        
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(compressed_files):
                selected_file = compressed_files[idx]
                console.print()
                query = Prompt.ask("[cyan]Enter query (e.g., 'severity=ERROR' or 'ip=1.2.3.4')[/cyan]")

                if not query:
                    console.print("[yellow]No query entered.[/yellow]")
                else:
                    # Parse simple key=value queries
                    key = None
                    val = None
                    if '=' in query:
                        parts = query.split('=', 1)
                        key = parts[0].strip().lower()
                        val = parts[1].strip()

                    if key not in ('severity', 'ip') or not val:
                        console.print("[red]Invalid query format. Use 'severity=ERROR' or 'ip=1.2.3.4'[/red]")
                    else:
                        console.print()
                        import subprocess
                        cmd = ["python", "-m", "logsim", "query", "-c", str(selected_file), "--limit", "50"]
                        if key == 'severity':
                            cmd += ["--severity", val]
                        else:
                            cmd += ["--ip", val]

                        # Run and stream output
                        result = subprocess.run(cmd, text=True, capture_output=True)
                        if result.stdout:
                            console.print(result.stdout)
                        if result.stderr:
                            console.print(f"[red]{result.stderr}[/red]")
        
        console.print()
        Prompt.ask("Press enter to continue")
    
    def run_evaluation(self):
        """Run full evaluation"""
        console.clear()
        console.print(Panel("Run Full Evaluation", style="cyan", box=box.DOUBLE))
        console.print()
        
        console.print("[yellow]This will run comprehensive evaluation on all datasets.[/yellow]")
        console.print("[yellow]This may take several minutes...[/yellow]")
        console.print()
        
        if Confirm.ask("Continue?", default=True):
            console.print()
            console.print("[cyan]Running full evaluation...[/cyan]")
            console.print()
            
            import subprocess
            # Use verbose evaluation for real-time progress display
            result = subprocess.run(
                ["python", "evaluation/run_verbose_evaluation.py"],
                cwd=Path.cwd(),
                text=True
            )
            
            console.print()
            console.print("[green]✓ Evaluation complete![/green]")
            console.print(f"Compressed files saved in [cyan]evaluation/compressed/[/cyan]")
        
        console.print()
        Prompt.ask("Press enter to continue")
    
    def benchmark_comparison(self):
        """Run benchmark comparison"""
        console.clear()
        console.print(Panel("Benchmark vs gzip", style="cyan", box=box.DOUBLE))
        console.print()
        
        console.print("[yellow]This will compare LogSim compression with gzip.[/yellow]")
        console.print()
        
        if Confirm.ask("Continue?", default=True):
            console.print()
            console.print("[cyan]Running benchmarks...[/cyan]")
            console.print()
            
            import subprocess
            # Stream output live so user can see progress
            result = subprocess.run(
                ["python", "evaluation/run_query_benchmarks.py"],
                cwd=Path.cwd(),
                text=True
            )
            
            console.print()
            console.print("[green]✓ Benchmarks complete![/green]")
        
        console.print()
        Prompt.ask("Press enter to continue")
    
    def view_results(self):
        """View evaluation results"""
        console.clear()
        console.print(Panel("View Results", style="cyan", box=box.DOUBLE))
        console.print()
        
        if not self.results_dir.exists():
            console.print("[red]No results found![/red]")
            Prompt.ask("Press enter to continue")
            return
        
        # List result files
        result_files = list(self.results_dir.glob("*.json")) + list(self.results_dir.glob("*.md"))
        
        if not result_files:
            console.print("[red]No result files found![/red]")
            Prompt.ask("Press enter to continue")
            return
        
        table = Table(title="📊 Available Results", box=box.ROUNDED)
        table.add_column("#", style="yellow", width=4)
        table.add_column("File", style="cyan")
        table.add_column("Size", justify="right", style="blue")
        
        for i, file in enumerate(result_files, 1):
            size_kb = file.stat().st_size / 1024
            table.add_row(str(i), file.name, f"{size_kb:.2f} KB")
        
        console.print(table)
        console.print()
        
        choice = Prompt.ask("Select file to view (or 'b' for back)", default="b")
        
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(result_files):
                selected_file = result_files[idx]
                console.print()
                console.print(f"[cyan]Contents of {selected_file.name}:[/cyan]")
                console.print()
                
                if selected_file.suffix == ".json":
                    import json
                    with open(selected_file) as f:
                        data = json.load(f)
                    console.print_json(data=data)
                else:
                    with open(selected_file) as f:
                        content = f.read()
                    console.print(content)
        
        console.print()
        Prompt.ask("Press enter to continue")
    
    def settings_menu(self):
        """Display and modify settings"""
        while True:
            console.clear()
            console.print(Panel("Settings & Configuration", style="cyan", box=box.DOUBLE))
            console.print()
            
            # Paths
            paths_table = Table(title="📂 Paths", box=box.SIMPLE)
            paths_table.add_column("Setting", style="yellow")
            paths_table.add_column("Value", style="cyan")
            paths_table.add_row("Datasets", str(self.data_dir))
            paths_table.add_row("Compressed", str(self.compressed_dir))
            paths_table.add_row("Results", str(self.results_dir))
            console.print(paths_table)
            console.print()
            
            # Available datasets
            if self.datasets:
                datasets_table = Table(title="📊 Available Datasets", box=box.SIMPLE)
                datasets_table.add_column("#", style="yellow", width=4)
                datasets_table.add_column("Name", style="cyan")
                datasets_table.add_column("Lines", justify="right", style="green")
                datasets_table.add_column("Size", justify="right", style="blue")
                
                for i, ds in enumerate(self.datasets, 1):
                    datasets_table.add_row(
                        str(i),
                        ds.name,
                        f"{ds.lines:,}",
                        f"{ds.size_mb:.2f} MB"
                    )
                
                console.print(datasets_table)
                console.print()
            
            # Settings
            settings_table = Table(title="🛠️  Compression Settings", box=box.SIMPLE)
            settings_table.add_column("#", style="yellow", width=4)
            settings_table.add_column("Setting", style="cyan")
            settings_table.add_column("Value", style="green")
            settings_table.add_row("[1]", "Min support", str(self.settings['min_support']))
            settings_table.add_row("[2]", "Zstd level", str(self.settings['zstd_level']))
            settings_table.add_row("[3]", "Enable BWT", str(self.settings['enable_bwt']))
            settings_table.add_row("[4]", "Measure metrics", str(self.settings['measure']))
            console.print(settings_table)
            console.print()
            
            console.print("[yellow]Options:[/yellow]")
            console.print("  [1-4] Modify setting")
            console.print("  [r]   Rescan datasets")
            console.print("  [b]   Back to main menu")
            console.print()
            
            choice = Prompt.ask("Select option", default="b")
            
            if choice == "1":
                new_val = IntPrompt.ask("Min support (2-10)", default=self.settings['min_support'])
                self.settings['min_support'] = max(2, min(10, new_val))
                console.print(f"[green]✓ Min support set to {self.settings['min_support']}[/green]")
                time.sleep(1)
            elif choice == "2":
                new_val = IntPrompt.ask("Zstd level (1-22)", default=self.settings['zstd_level'])
                self.settings['zstd_level'] = max(1, min(22, new_val))
                console.print(f"[green]✓ Zstd level set to {self.settings['zstd_level']}[/green]")
                time.sleep(1)
            elif choice == "3":
                self.settings['enable_bwt'] = not self.settings['enable_bwt']
                console.print(f"[green]✓ BWT {'enabled' if self.settings['enable_bwt'] else 'disabled'}[/green]")
                time.sleep(1)
            elif choice == "4":
                self.settings['measure'] = not self.settings['measure']
                console.print(f"[green]✓ Metrics measurement {'enabled' if self.settings['measure'] else 'disabled'}[/green]")
                time.sleep(1)
            elif choice.lower() == "r":
                console.print("[cyan]Rescanning datasets...[/cyan]")
                self.datasets = self.scan_datasets()
                console.print(f"[green]✓ Found {len(self.datasets)} datasets[/green]")
                time.sleep(1)
            elif choice.lower() == "b":
                break
            else:
                console.print("[red]Invalid option![/red]")
                time.sleep(1)
    
    def run(self):
        """Main loop"""
        # Scan datasets
        self.datasets = self.scan_datasets()
        
        if not self.datasets:
            console.print("[yellow]Warning: No datasets found in data/datasets/[/yellow]")
            console.print("[yellow]You can still use other features.[/yellow]")
            time.sleep(2)
        
        # Main loop
        while True:
            try:
                self.show_main_menu()
            except KeyboardInterrupt:
                console.print("\n[yellow]Exiting...[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                console.print_exception()
                Prompt.ask("Press enter to continue")


def main():
    """Entry point"""
    cli = InteractiveCLI()
    cli.run()


if __name__ == '__main__':
    main()
