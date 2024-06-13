from flask import Blueprint, jsonify, redirect, render_template, request, url_for, Response
from triggers import TriggerGame, TriggerOffers

index = Blueprint('index', __name__)

@index.route('/')
def get_index():
    return render_template('index.html')

@index.route('/juego', methods=["POST"])
def get_juego():
    scrape = TriggerGame()
    result = scrape.parse_data(request.form.get('game-link'))
    return jsonify(result)

@index.route('/ofertas')
def get_ofertas_page():
    return render_template('ofertas.html')

@index.route('/ofertas', methods=['POST'])
def get_ofertas():
    scrape = TriggerOffers()
    result = scrape.parse_data()
    return jsonify(result)