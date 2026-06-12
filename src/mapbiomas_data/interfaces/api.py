import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from flask import Flask, jsonify, request
except ImportError:
    Flask = None

from mapbiomas_data.config import ConfigLoader
from mapbiomas_data.core import DatasetManager, TerritoryManager, VisualizationManager

app = Flask(__name__) if Flask else None

config = ConfigLoader()
config.load_all()
datasets_mgr = DatasetManager(config)
territories_mgr = TerritoryManager(config)
viz_mgr = VisualizationManager(config)


def create_app():
    if app is None:
        return None

    @app.route("/")
    def home():
        return jsonify({
            "name": "MapBiomas GIF Factory API",
            "version": "0.1.0",
            "endpoints": {
                "/categories": "Listar categorias",
                "/datasets": "Listar datasets",
                "/datasets/<id>/products": "Listar produtos de um dataset",
                "/territories": "Listar territórios",
                "/territories/<id>": "Detalhes de um território",
                "/visualizations": "Listar visualizações",
                "/visualizations/<key>": "Detalhes de uma visualização",
                "/generate": "Gerar GIF (POST)",
            },
        })

    @app.route("/categories")
    def list_categories():
        return jsonify(datasets_mgr.list_categories())

    @app.route("/datasets")
    def list_datasets():
        category = request.args.get("category")
        return jsonify(datasets_mgr.list_datasets(category))

    @app.route("/datasets/<dataset_id>/products")
    def list_products(dataset_id: str):
        try:
            return jsonify(datasets_mgr.list_products(dataset_id))
        except KeyError as e:
            return jsonify({"error": str(e)}), 404

    @app.route("/datasets/<dataset_id>/products/<product_id>")
    def get_product(dataset_id: str, product_id: str):
        try:
            return jsonify(datasets_mgr.get_product(dataset_id, product_id))
        except KeyError as e:
            return jsonify({"error": str(e)}), 404

    @app.route("/territories")
    def list_territories():
        ttype = request.args.get("type")
        return jsonify(territories_mgr.list_territories(ttype))

    @app.route("/territories/<territory_id>")
    def get_territory(territory_id: str):
        try:
            return jsonify(territories_mgr.get_territory(territory_id))
        except KeyError as e:
            return jsonify({"error": str(e)}), 404

    @app.route("/visualizations")
    def list_visualizations():
        keys = viz_mgr.list_viz_keys()
        return jsonify({k: viz_mgr.get_viz_params(k) for k in keys})

    @app.route("/visualizations/<viz_key>")
    def get_visualization(viz_key: str):
        try:
            return jsonify(viz_mgr.get_viz_params(viz_key))
        except KeyError as e:
            return jsonify({"error": str(e)}), 404

    @app.route("/generate", methods=["POST"])
    def generate():
        data = request.get_json()
        dataset_id = data.get("dataset")
        product_id = data.get("product")
        territory_id = data.get("territory", "uf_df")
        viz_key = data.get("visualization", "fire")

        if not dataset_id or not product_id:
            return jsonify({"error": "dataset and product are required"}), 400

        try:
            ds_info = datasets_mgr.get_product(dataset_id, product_id)
            t_info = territories_mgr.get_territory(territory_id)
            viz_params = viz_mgr.get_viz_params(viz_key)

            return jsonify({
                "status": "configured",
                "dataset": dataset_id,
                "product": product_id,
                "product_name": ds_info.get("name", ""),
                "territory": territory_id,
                "territory_name": t_info["name"],
                "visualization": viz_key,
                "asset": ds_info.get("asset", ""),
                "palette_size": len(viz_params["palette"]),
                "message": "GIF generation will be implemented with Earth Engine integration",
            })
        except KeyError as e:
            return jsonify({"error": str(e)}), 404

    return app


def run_api(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    if Flask is None:
        print("Flask não está instalado. Execute: pip install flask")
        return
    application = create_app()
    if application:
        application.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_api(debug=True)
