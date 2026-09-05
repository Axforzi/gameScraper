import logging
import re

import crochet
from flask import Blueprint, jsonify, render_template, request

from triggers import TriggerGame, TriggerOffers

index = Blueprint('index', __name__)

logger = logging.getLogger(__name__)

GAME_LINK_MAX_LENGTH = 200
GAME_LINK_PATTERN = re.compile(r"^[A-Za-z0-9 \-\&'.,:!()+]+$")

TIMEOUT_JUEGO_MSG = "La búsqueda tardó demasiado. Intenta de nuevo."
TIMEOUT_OFERTAS_MSG = "La consulta de ofertas tardó demasiado. Intenta de nuevo."
FAILED_JUEGO_MSG = "No se pudieron obtener resultados para tu búsqueda."
FAILED_OFERTAS_MSG = "No se pudieron obtener las ofertas."


def _validate_game_link(value):
    """Validate the ``game-link`` search term (REQ-SEC-3).

    The field is a search term passed to the spiders as ``juego=``, not a URL.
    Rules: strip -> non-empty, length-bounded, allowlist pattern, no control
    or HTML characters. Returns an error message or None when valid.
    """
    if value is None:
        return "El campo de búsqueda es obligatorio."
    term = value.strip()
    if not term:
        return "El campo de búsqueda no puede estar vacío."
    if len(term) > GAME_LINK_MAX_LENGTH:
        return "El término de búsqueda no puede superar los 200 caracteres."
    if not GAME_LINK_PATTERN.fullmatch(term):
        return "El término de búsqueda contiene caracteres no permitidos."
    return None


def _payload_with_errors(result, scrape):
    """Attach per-store errors to a 200 partial response (REQ-ASM-3)."""
    payload = dict(result)
    if scrape.errors:
        payload['errors'] = scrape.errors
    return payload


def _total_failure(result, scrape):
    """True when every spider failed and nothing was scraped (REQ-ASM-3)."""
    return bool(scrape.errors) and not any(result.values())


@index.route('/')
def get_index():
    return render_template('index.html')


@index.route('/juego', methods=["POST"])
def get_juego():
    term = request.form.get('game-link')
    error = _validate_game_link(term)
    if error:
        return jsonify({'error': error}), 400

    scrape = TriggerGame()
    try:
        result = scrape.parse_data(term.strip())
    except crochet.TimeoutError:
        logger.warning("juego request timed out; partial=%s", scrape.items)
        return jsonify({**scrape.items, 'error': TIMEOUT_JUEGO_MSG}), 504
    except Exception:
        logger.exception("juego trigger failed for term=%r", term)
        return jsonify({'error': FAILED_JUEGO_MSG}), 502

    if _total_failure(result, scrape):
        return jsonify({'error': FAILED_JUEGO_MSG, 'errors': scrape.errors}), 502
    return jsonify(_payload_with_errors(result, scrape))


@index.route('/ofertas')
def get_ofertas_page():
    return render_template('ofertas.html')


@index.route('/ofertas', methods=['POST'])
def get_ofertas():
    scrape = TriggerOffers()
    try:
        result = scrape.parse_data()
    except crochet.TimeoutError:
        logger.warning("ofertas request timed out; partial=%s", scrape.items)
        return jsonify({**scrape.items, 'error': TIMEOUT_OFERTAS_MSG}), 504
    except Exception:
        logger.exception("ofertas trigger failed")
        return jsonify({'error': FAILED_OFERTAS_MSG}), 502

    if _total_failure(result, scrape):
        return jsonify({'error': FAILED_OFERTAS_MSG, 'errors': scrape.errors}), 502
    return jsonify(_payload_with_errors(result, scrape))