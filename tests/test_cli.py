import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from ipam_gif_factory.interfaces.cli import CLI


@pytest.fixture
def cli():
    return CLI()


class TestCLI:
    def test_list_categories(self, cli, capsys):
        cli.run(["--list-categories"])
        captured = capsys.readouterr()
        assert "Fogo" in captured.out or "fogo" in captured.out.lower()

    def test_list_datasets(self, cli, capsys):
        cli.run(["--list-datasets"])
        captured = capsys.readouterr()
        assert "brasil_fire_col3" in captured.out

    def test_list_products(self, cli, capsys):
        cli.run(["--list-products", "brasil_fire_col3"])
        captured = capsys.readouterr()
        assert "annual_burned" in captured.out
        assert "monthly_burned" in captured.out

    def test_list_products_invalid(self, cli, capsys):
        cli.run(["--list-products", "nonexistent"])
        captured = capsys.readouterr()
        assert "Erro" in captured.out or "não encontrado" in captured.out

    def test_list_territories(self, cli, capsys):
        cli.run(["--list-territories"])
        captured = capsys.readouterr()
        assert "Distrito Federal" in captured.out
        assert "df" in captured.out

    def test_list_territories_states(self, cli, capsys):
        cli.run(["--list-territories", "states"])
        captured = capsys.readouterr()
        assert "Distrito Federal" in captured.out

    def test_list_viz(self, cli, capsys):
        cli.run(["--list-viz"])
        captured = capsys.readouterr()
        assert "fire" in captured.out

    def test_generate_without_args(self, cli, capsys):
        cli.run(["--generate"])
        captured = capsys.readouterr()
        assert "obrigatórios" in captured.out or "Erro" in captured.out

    def test_validate(self, cli, capsys):
        cli.run(["--validate"])
        captured = capsys.readouterr()
        assert "Válido" in captured.out or "OK" in captured.out or "Tudo" in captured.out

    def test_help(self, cli, capsys):
        try:
            cli.run(["--help"])
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert "Gerar GIF" in captured.out
        assert "Earth" in captured.out

    def test_list_territories_countries(self, cli, capsys):
        cli.run(["--list-territories", "countries"])
        captured = capsys.readouterr()
        assert "Brasil" in captured.out
        assert "Paraguai" in captured.out

    def test_list_territories_biomes(self, cli, capsys):
        cli.run(["--list-territories", "biomes"])
        captured = capsys.readouterr()
        assert "Cerrado" in captured.out or "Amazônia" in captured.out
