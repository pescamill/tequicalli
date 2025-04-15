from flask import Flask, request, redirect, url_for, render_template
from werkzeug.utils import secure_filename
import uuid
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
import os
import click # 

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tequicalli.db'
db = SQLAlchemy(app)
migrate = Migrate(app,db)
login_manager = LoginManager(app)

# Base directory for all uploads within the container
BASE_UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')

# Specific subdirectories for different models/types
CLIENT_IMAGE_FOLDER = os.path.join(BASE_UPLOAD_FOLDER, 'client_images')

# Ensure all directories exist
os.makedirs(CLIENT_IMAGE_FOLDER, exist_ok=True)

# You might store these paths in app.config if preferred
app.config['CLIENT_IMAGE_FOLDER'] = CLIENT_IMAGE_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Helper function (as before)
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'admin' or 'worker'

# House model
class House(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rooms = db.relationship('Room', backref='house', lazy=True)

# Room model
class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'), nullable=False)
    rents = db.relationship('RentRecord', backref='room', lazy=True)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    image_file = db.Column(db.String(100), nullable=True, default=None)

 # Optional: Property to easily get the image URL
    @property
    def image_url(self):
        if self.image_file:
            # Assumes images are stored in static/uploads/client_images
            # Adjust the path if your UPLOAD_FOLDER is different
            return url_for('static', filename=f'uploads/client_images/{self.image_file}')
        else:
            # Return path to a default placeholder image or None
            return url_for('static', filename='uploads/client_images/default.png') # Example placeholder

# Rent record model
class RentRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True)

# Optional: create DB on first run
@app.cli.command("init-db")
def init_db_command():
    """Creates the database tables."""
    db.create_all()
    click.echo("Initialized the database.")

# Login manager

@login_manager.user_loader
def load_user(user_id):
    # user_id comes from the session cookie, usually as a string
    # You need to query your database for the user with this ID
    try:
        # Convert user_id to an integer for querying
        user_id_int = int(user_id)
        # Query the User table using the primary key (id)
        return User.query.get(user_id_int)
    except ValueError:
        # Handle cases where user_id is not a valid integer
        return None
    except Exception as e:
        # Handle potential database errors, log the error
        print(f"Error loading user {user_id}: {e}") # Basic error logging
        return None

@app.route('/')
def index():
    return render_template('layout.html')

@app.route('/twice')
def twice():
    return render_template('twice.html')

@app.route('/houses', methods=['GET'])
def houses():
    all_houses = House.query.all()
    return render_template('houses.html', houses=all_houses)

@app.route('/add_house', methods=['POST'])
def add_house():
    name = request.form['name']
    db.session.add(House(name=name))
    db.session.commit()
    return redirect(url_for('houses'))

@app.route('/rooms', methods=['GET'])
def rooms():
    all_rooms = Room.query.all()
    all_houses = House.query.all()
    return render_template('rooms.html', rooms=all_rooms, houses=all_houses)

@app.route('/add_room', methods=['POST'])
def add_room():
    name = request.form['name']
    house_id = request.form['house_id']
    db.session.add(Room(name=name, house_id=house_id))
    db.session.commit()
    return redirect(url_for('rooms'))

@app.route('/clients', methods=['GET'])
def clients():
    all_clients = Client.query.all()
    return render_template('clients.html', clients=all_clients)

@app.route('/add_client', methods=['POST'])
def add_client():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    db.session.add(Client(name=name, email=email, phone=phone))
    db.session.commit()
    return redirect(url_for('clients'))

@app.route('/rents', methods=['GET'])
def rents():
    all_rents = RentRecord.query.all()
    all_rooms = Room.query.all()
    all_clients = Client.query.all()
    return render_template('rents.html', rents=all_rents, rooms=all_rooms, clients=all_clients)

@app.route('/add_rent', methods=['POST'])
def add_rent():
    from datetime import datetime
    date = datetime.strptime(request.form['date'], '%Y-%m-%d')
    amount = float(request.form['amount'])
    room_id = request.form['room_id']
    client_id = request.form.get('client_id') or None
    db.session.add(RentRecord(date=date, amount=amount, room_id=room_id, client_id=client_id))
    db.session.commit()
    return redirect(url_for('rents'))