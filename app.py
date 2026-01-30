#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API Flask que expõe as funções do KW Planner (arquivo-base-fixed.py) para uso web.
O frontend (GitHub Pages) chama estes endpoints e exibe os resultados.
"""

import os
import sys
import io
import importlib.util
import json
import re
from collections import deque

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Permite chamadas do frontend em GitHub Pages (origem diferente)

# Caminho para a pasta app (onde está arquivo-base-fixed.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "..", "app")
SCRIPT_PATH = os.path.join(APP_DIR, "arquivo-base-fixed.py")

if not os.path.exists(SCRIPT_PATH):
    SCRIPT_PATH = os.path.join(BASE_DIR, "..", "app", "arquivo-base-fixed.py")
if not os.path.exists(SCRIPT_PATH):
    raise FileNotFoundError(f"Script não encontrado: {SCRIPT_PATH}. Coloque arquivo-base-fixed.py em KW Planner/app/.")

sys.path.insert(0, APP_DIR)


def load_script_module():
    """Carrega o módulo arquivo-base-fixed como um módulo Python."""
    spec = importlib.util.spec_from_file_location("kw_script", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    return spec, module


def run_analysis(option, input_responses, timeout_seconds=600):
    """
    Executa uma análise do script com input() e save_to_csv_simple mockados.
    option: 1=site, 2=nicho, 3=url, 4=variações, 5=tema, 6=content pruning, 7=dashboard, 8=export
    input_responses: lista de strings para simular input() em ordem
    Retorna: (stdout_text, exports_list, error_message)
    """
    stdout_capture = io.StringIO()
    exports = []  # [{ "filename": "...", "data": [...] }, ...]
    input_queue = deque(input_responses)

    def mock_input(prompt=""):
        if input_queue:
            return input_queue.popleft().strip()
        return ""

    def mock_save_to_csv_simple(data, filename):
        exports.append({"filename": filename, "data": data})
        return True

    spec, script_module = load_script_module()
    spec.loader.exec_module(script_module)

    # Patches: o script usa input() builtin e save_to_csv_simple / save_to_csv_simple_pruning do módulo
    script_module.save_to_csv_simple = mock_save_to_csv_simple
    script_module.save_to_csv_simple_pruning = mock_save_to_csv_simple
    builtins = __import__("builtins")
    original_input = builtins.input
    builtins.input = mock_input
    old_stdout = sys.stdout
    sys.stdout = stdout_capture
    old_cwd = os.getcwd()
    try:
        os.chdir(APP_DIR)  # script espera arquivos (keyword_learning.db, etc.) na pasta app
    except OSError:
        pass

    try:
        if option == 1:
            script_module.run_site_analysis()
        elif option == 2:
            script_module.run_niche_analysis()
        elif option == 3:
            script_module.run_url_analysis()
        elif option == 4:
            script_module.run_keyword_variations()
        elif option == 5:
            script_module.run_theme_analysis()
        elif option == 6:
            script_module.run_content_pruning_analysis()
        elif option == 7:
            script_module.show_learning_dashboard()
        elif option == 8:
            script_module.export_learning_data()
        else:
            return "", [], f"Opção inválida: {option}"
    except Exception as e:
        return stdout_capture.getvalue(), exports, str(e)
    finally:
        builtins.input = original_input
        sys.stdout = old_stdout
        try:
            os.chdir(old_cwd)
        except OSError:
            pass

    return stdout_capture.getvalue(), exports, None


@app.route("/api/health", methods=["GET"])
def health():
    """Verifica se a API está no ar."""
    return jsonify({"status": "ok", "message": "KW Planner API"}), 200


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """
    Executa uma análise.
    Body JSON: { "option": 1-8, "params": { ... } }
    option 1: params.domain_url, params.include_subdomains (opcional, default false)
    option 2: params.niche
    option 3: params.url
    option 4: params.keyword
    option 5: params.domain_url, params.theme
    option 6: params.domain_url, params.include_subdomains (opcional)
    option 7, 8: sem params
    """
    try:
        data = request.get_json() or {}
        option = int(data.get("option", 0))
        params = data.get("params", {})

        if option == 1:
            domain_url = (params.get("domain_url") or "").strip()
            if not domain_url:
                return jsonify({"error": "domain_url é obrigatório"}), 400
            if not domain_url.startswith(("http://", "https://")):
                domain_url = "https://" + domain_url
            include_sub = params.get("include_subdomains", False)
            input_responses = [domain_url, "s" if include_sub else "n"]
        elif option == 2:
            niche = (params.get("niche") or "").strip()
            if not niche:
                return jsonify({"error": "niche é obrigatório"}), 400
            input_responses = [niche]
        elif option == 3:
            url = (params.get("url") or "").strip()
            if not url:
                return jsonify({"error": "url é obrigatório"}), 400
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            input_responses = [url]
        elif option == 4:
            keyword = (params.get("keyword") or "").strip()
            if not keyword:
                return jsonify({"error": "keyword é obrigatório"}), 400
            input_responses = [keyword]
        elif option == 5:
            domain_url = (params.get("domain_url") or "").strip()
            theme = (params.get("theme") or "").strip()
            if not domain_url or not theme:
                return jsonify({"error": "domain_url e theme são obrigatórios"}), 400
            if not domain_url.startswith(("http://", "https://")):
                domain_url = "https://" + domain_url
            input_responses = [domain_url, theme]
        elif option == 6:
            domain_url = (params.get("domain_url") or "").strip()
            if not domain_url:
                return jsonify({"error": "domain_url é obrigatório"}), 400
            if not domain_url.startswith(("http://", "https://")):
                domain_url = "https://" + domain_url
            include_sub = params.get("include_subdomains", False)
            input_responses = [domain_url, "s" if include_sub else "n"]
        elif option in (7, 8):
            input_responses = []
        else:
            return jsonify({"error": "option deve ser entre 1 e 8"}), 400

        output_text, exports, err = run_analysis(option, input_responses)
        if err:
            return jsonify({
                "output": output_text,
                "exports": [],
                "error": err,
            }), 200  # 200 para o frontend poder ler output + error

        return jsonify({
            "output": output_text,
            "exports": exports,
            "error": None,
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
