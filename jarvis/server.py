"""
JARVIS Flask Status Server — lightweight health endpoint.
"""
from flask import Flask, jsonify
from datetime import datetime
import psutil


def create_app():
    app = Flask(__name__)

    @app.route("/status", methods=["GET"])
    def status():
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.5)
        return jsonify({
            "status": "online",
            "name": "JARVIS",
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_percent": cpu,
                "ram_percent": mem.percent,
                "ram_used_gb": round(mem.used / 1e9, 2)
            }
        })

    @app.route("/", methods=["GET"])
    def root():
        return jsonify({"message": "JARVIS is running. Visit /status for health info."})

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=False)
