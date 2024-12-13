from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_httpauth import HTTPBasicAuth
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
db = SQLAlchemy(app)
auth = HTTPBasicAuth()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_librarian = db.Column(db.Boolean, default=False)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)

class BorrowRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    approved = db.Column(db.Boolean, default=False)

@auth.verify_password
def verify_password(email, password):
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        return user

@app.route('/librarian/create_user', methods=['POST'])
@auth.login_required
def create_user():
    if not auth.current_user().is_librarian:
        return jsonify({'error': 'Access denied'}), 403
    data = request.json
    hashed_password = generate_password_hash(data['password'], method='sha256')
    new_user = User(email=data['email'], password=hashed_password, is_librarian=data.get('is_librarian', False))
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User created successfully'})

@app.route('/librarian/borrow_requests', methods=['GET'])
@auth.login_required
def view_borrow_requests():
    if not auth.current_user().is_librarian:
        return jsonify({'error': 'Access denied'}), 403
    requests = BorrowRequest.query.all()
    return jsonify([{
        'user_id': req.user_id,
        'book_id': req.book_id,
        'start_date': req.start_date,
        'end_date': req.end_date,
        'approved': req.approved
    } for req in requests])

@app.route('/librarian/approve_request/<int:request_id>', methods=['POST'])
@auth.login_required
def approve_request(request_id):
    if not auth.current_user().is_librarian:
        return jsonify({'error': 'Access denied'}), 403
    borrow_request = BorrowRequest.query.get(request_id)
    if borrow_request:
        borrow_request.approved = True
        db.session.commit()
        return jsonify({'message': 'Request approved'})
    return jsonify({'error': 'Request not found'}), 404

@app.route('/user/books', methods=['GET'])
@auth.login_required
def get_books():
    books = Book.query.all()
    return jsonify([{'id': book.id, 'title': book.title} for book in books])

@app.route('/user/borrow', methods=['POST'])
@auth.login_required
def borrow_book():
    data = request.json
    start_date = datetime.datetime.strptime(data['start_date'], '%Y-%m-%d').date()
    end_date = datetime.datetime.strptime(data['end_date'], '%Y-%m-%d').date()
    
    overlapping_request = BorrowRequest.query.filter(
        BorrowRequest.book_id == data['book_id'],
        BorrowRequest.end_date >= start_date,
        BorrowRequest.start_date <= end_date,
        BorrowRequest.approved == True
    ).first()
    
    if overlapping_request:
        return jsonify({'error': 'Book already borrowed during this period'}), 400
    
    new_request = BorrowRequest(user_id=auth.current_user().id, book_id=data['book_id'],
                                start_date=start_date, end_date=end_date)
    db.session.add(new_request)
    db.session.commit()
    return jsonify({'message': 'Borrow request submitted'})

@app.route('/user/borrow_history', methods=['GET'])
@auth.login_required
def borrow_history():
    requests = BorrowRequest.query.filter_by(user_id=auth.current_user().id).all()
    return jsonify([{
        'book_id': req.book_id,
        'start_date': req.start_date,
        'end_date': req.end_date,
        'approved': req.approved
    } for req in requests])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0',port= 9000,debug=True)