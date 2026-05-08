import typer

app = typer.Typer(help="LECSEG command line interface.")


@app.command()
def download():
    """Download datasets or lecture videos."""
    typer.echo("download: not implemented yet")


@app.command()
def transcribe():
    """Transcribe audio using Whisper."""
    typer.echo("transcribe: not implemented yet")


@app.command()
def ocr():
    """Run OCR on lecture frames/slides."""
    typer.echo("ocr: not implemented yet")


@app.command()
def shots():
    """Detect shot or slide changes."""
    typer.echo("shots: not implemented yet")


@app.command()
def prosody():
    """Extract audio/prosody features."""
    typer.echo("prosody: not implemented yet")


@app.command()
def embed():
    """Create text/visual embeddings."""
    typer.echo("embed: not implemented yet")


@app.command()
def segment():
    """Run topic segmentation."""
    typer.echo("segment: not implemented yet")


@app.command()
def evaluate():
    """Evaluate segmentation results."""
    typer.echo("evaluate: not implemented yet")


@app.command()
def report():
    """Generate reports and thesis artifacts."""
    typer.echo("report: not implemented yet")


@app.command()
def run():
    """Run the full pipeline."""
    typer.echo("run: not implemented yet")


if __name__ == "__main__":
    app()
