from pathlib import Path
import pytest
from click.testing import CliRunner
from teachbooks.cli import main as commands

WORK_DIR = Path(__file__).parent / ".teachbooks"
PATH_BOOK = Path(__file__).parent / "book"

@pytest.fixture()
def cli():
    """Provides a click.testing CliRunner object for invoking CLI commands."""
    runner = CliRunner()
    yield runner
    del runner

def test_build(cli: CliRunner):
    build_result = cli.invoke(
        commands.build,
        PATH_BOOK.as_posix()
    )
    assert build_result.exit_code == 0, build_result.output
    html = PATH_BOOK.joinpath("_build", "html")
    assert html.joinpath("index.html").exists()
    _ = cli.invoke(commands.clean,
                   PATH_BOOK.as_posix())
    assert not html.joinpath("index.html").exists()
