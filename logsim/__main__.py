"""
Entry point for python -m logsim
"""

import click
from logsim.cli import compress, query

@click.group()
@click.version_option(version='1.0.0')
def cli():
    """LogSim - Semantic Log Compression System"""
    pass

cli.add_command(compress)
cli.add_command(query)

if __name__ == '__main__':
    cli()
