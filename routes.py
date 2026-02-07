from flask import Blueprint, request, jsonify
from app import db
from models import User, Portfolio, Order
import yfinance as yf
from functools import wraps
import jwt
import os
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)
trading_bp = Blueprint('trading', __name__)
stock_bp = Blueprint('stock', __name__)

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')

# JWT Token decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            token = token.split(' ')[1]
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'message': 'Invalid token!'}), 401
        except:
            return jsonify({'message': 'Invalid token!'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

# AUTH ROUTES
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Username already exists'}), 400
    
    user = User(username=data['username'], email=data['email'])
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'User registered successfully', 'user': user.to_dict()}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Missing username or password'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    token = jwt.encode(
        {'user_id': user.id, 'exp': datetime.utcnow() + timedelta(days=30)},
        SECRET_KEY,
        algorithm='HS256'
    )
    
    return jsonify({'message': 'Login successful', 'token': token, 'user': user.to_dict()}), 200

# TRADING ROUTES
@trading_bp.route('/dashboard', methods=['GET'])
@token_required
def dashboard(current_user):
    portfolio = Portfolio.query.filter_by(user_id=current_user.id).all()
    recent_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).limit(10).all()
    
    return jsonify({
        'user': current_user.to_dict(),
        'portfolio': [p.to_dict() for p in portfolio],
        'recent_orders': [o.to_dict() for o in recent_orders]
    }), 200

@trading_bp.route('/buy', methods=['POST'])
@token_required
def buy(current_user):
    data = request.get_json()
    symbol = data.get('stock_symbol', '').upper()
    quantity = data.get('quantity', 0)
    
    if not symbol or quantity <= 0:
        return jsonify({'message': 'Invalid symbol or quantity'}), 400
    
    try:
        ticker = yf.Ticker(symbol)
        current_price = ticker.info.get('currentPrice')
        if not current_price:
            return jsonify({'message': 'Stock not found'}), 404
    except:
        return jsonify({'message': 'Error fetching stock price'}), 500
    
    total_cost = current_price * quantity
    
    if current_user.balance < total_cost:
        return jsonify({'message': 'Insufficient balance'}), 400
    
    current_user.balance -= total_cost
    
    portfolio = Portfolio.query.filter_by(user_id=current_user.id, stock_symbol=symbol).first()
    if portfolio:
        portfolio.average_price = (portfolio.average_price * portfolio.quantity + current_price * quantity) / (portfolio.quantity + quantity)
        portfolio.quantity += quantity
    else:
        portfolio = Portfolio(user_id=current_user.id, stock_symbol=symbol, quantity=quantity, average_price=current_price)
        db.session.add(portfolio)
    
    order = Order(user_id=current_user.id, stock_symbol=symbol, order_type='BUY', quantity=quantity, price=current_price, total_value=total_cost)
    db.session.add(order)
    db.session.commit()
    
    return jsonify({'message': 'Buy order successful', 'order': order.to_dict()}), 201

@trading_bp.route('/sell', methods=['POST'])
@token_required
def sell(current_user):
    data = request.get_json()
    symbol = data.get('stock_symbol', '').upper()
    quantity = data.get('quantity', 0)
    
    if not symbol or quantity <= 0:
        return jsonify({'message': 'Invalid symbol or quantity'}), 400
    
    portfolio = Portfolio.query.filter_by(user_id=current_user.id, stock_symbol=symbol).first()
    if not portfolio or portfolio.quantity < quantity:
        return jsonify({'message': 'Insufficient shares'}), 400
    
    try:
        ticker = yf.Ticker(symbol)
        current_price = ticker.info.get('currentPrice')
        if not current_price:
            return jsonify({'message': 'Stock not found'}), 404
    except:
        return jsonify({'message': 'Error fetching stock price'}), 500
    
    total_revenue = current_price * quantity
    
    current_user.balance += total_revenue
    
    portfolio.quantity -= quantity
    if portfolio.quantity == 0:
        db.session.delete(portfolio)
    
    order = Order(user_id=current_user.id, stock_symbol=symbol, order_type='SELL', quantity=quantity, price=current_price, total_value=total_revenue)
    db.session.add(order)
    db.session.commit()
    
    return jsonify({'message': 'Sell order successful', 'order': order.to_dict()}), 201

# STOCK DATA ROUTES
@stock_bp.route('/price/<symbol>', methods=['GET'])
def get_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.info
        return jsonify({
            'symbol': symbol,
            'price': data.get('currentPrice'),
            'name': data.get('longName'),
            'currency': data.get('currency')
        }), 200
    except:
        return jsonify({'message': 'Stock not found'}), 404

@stock_bp.route('/history/<symbol>', methods=['GET'])
def get_history(symbol):
    period = request.args.get('period', '1mo')
    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period=period)
        history_data = history.reset_index().to_dict('records')
        return jsonify({'symbol': symbol, 'period': period, 'data': history_data}), 200
    except:
        return jsonify({'message': 'Error fetching history'}), 500
