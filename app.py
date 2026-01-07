from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
from models import db, Admin, Quiz, QuizItem, GameSession, Participant, ParticipantAnswer
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from google.cloud import storage
from dotenv import load_dotenv
import os
import csv
import zipfile
import shutil
from io import BytesIO, StringIO
from pathlib import Path
from datetime import datetime, timezone
import random
import string

app = Flask(__name__, static_folder='static', static_url_path='', template_folder='templates')

# Configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///dragdrop_quiz.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
db.init_app(app)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Configure CORS for API routes

# Socket.IO configuration
# async_mode is auto-detected based on installed packages (eventlet is in requirements.txt)
socketio = SocketIO(app, cors_allowed_origins="*")

# Create database tables and upload folder (only once)
def init_db():
    with app.app_context():
        db.create_all()
        print("Database tables created!")

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# GCS configuration
GCS_BUCKET_NAME = 'drag-drop-quiz-uploads'
gcs_client = None

def get_gcs_client():
    global gcs_client
    if gcs_client is None:
        try:
            gcs_client = storage.Client()
        except Exception as e:
            print(f"Warning: Could not initialize GCS client: {e}")
            return None
    return gcs_client

def upload_file_to_gcs(file_content, filename):
    """Upload file to Google Cloud Storage and return public URL"""
    try:
        client = get_gcs_client()
        if client is None:
            # Fallback to local storage if GCS unavailable
            return upload_file_locally(file_content, filename)
        
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(file_content, content_type='image/webp')
        # Make blob publicly readable
        blob.make_public()
        return blob.public_url
    except Exception as e:
        print(f"GCS upload error: {e}. Falling back to local storage.")
        return upload_file_locally(file_content, filename)

def upload_file_locally(file_content, filename):
    """Fallback: Upload file to local filesystem"""
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with open(filepath, 'wb') as f:
        if isinstance(file_content, bytes):
            f.write(file_content)
        else:
            f.write(file_content.read())
    return f"/static/uploads/{filename}"

# Helper function to generate game code
def generate_game_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# Helper functions for import/export
def get_next_filename(base_name, directory):
    """Generate unique filename if it already exists"""
    path = Path(directory)
    name, ext = os.path.splitext(base_name)
    counter = 1
    new_name = base_name
    
    while (path / new_name).exists():
        new_name = f"{name}_{counter}{ext}"
        counter += 1
    
    return new_name

def validate_image_file(filename):
    """Check if file is a valid image"""
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def export_quiz_to_zip(quiz_id, admin_id):
    """Export quiz with images as ZIP file"""
    quiz = Quiz.query.filter_by(quiz_id=quiz_id, admin_id=admin_id).first()
    if not quiz:
        return None, "Quiz not found"
    
    items = QuizItem.query.filter_by(quiz_id=quiz_id).order_by(QuizItem.item_order).all()
    
    # Create in-memory ZIP
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Create CSV content
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerow(['text', 'correct_position', 'item_order', 'image_file'])
        
        # Track filenames to handle duplicates
        filename_map = {}
        
        for item in items:
            # Get original filename or extract from URL
            if item.original_filename:
                base_filename = item.original_filename
            else:
                base_filename = os.path.basename(item.image_url)
            
            # Handle duplicate filenames
            if base_filename in filename_map:
                name, ext = os.path.splitext(base_filename)
                filename_map[base_filename] += 1
                unique_filename = f"{name}_{filename_map[base_filename]}{ext}"
            else:
                filename_map[base_filename] = 0
                unique_filename = base_filename
            
            csv_writer.writerow([
                item.text or '',
                item.correct_position,
                item.item_order,
                unique_filename
            ])
            
            # Add image to ZIP
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(item.image_url))
            if os.path.exists(image_path):
                zip_file.write(image_path, arcname=f"images/{unique_filename}")
        
        # Add CSV to ZIP
        csv_content = csv_buffer.getvalue()
        zip_file.writestr('quiz.csv', csv_content)
        
        # Add metadata
        metadata = f"title,{quiz.title}\n"
        metadata += f"description,{quiz.description or ''}\n"
        metadata += f"num_positions,{quiz.num_positions}\n"
        zip_file.writestr('metadata.txt', metadata)
    
    zip_buffer.seek(0)
    return zip_buffer, None

def import_quiz_from_zip(zip_file, admin_id):
    """Import quiz from ZIP file"""
    try:
        zip_buffer = BytesIO(zip_file.read())
        zip_buffer.seek(0)
        
        with zipfile.ZipFile(zip_buffer, 'r') as zip_obj:
            # Validate required files
            if 'quiz.csv' not in zip_obj.namelist():
                return None, "Missing quiz.csv in ZIP file"
            
            # Read metadata
            metadata = {}
            if 'metadata.txt' in zip_obj.namelist():
                with zip_obj.open('metadata.txt') as f:
                    lines = f.read().decode('utf-8').split('\n')
                    for line in lines:
                        if ',' in line:
                            key, value = line.split(',', 1)
                            metadata[key] = value
            
            # Read CSV
            with zip_obj.open('quiz.csv') as f:
                csv_reader = csv.DictReader(f.read().decode('utf-8').splitlines())
                items_data = list(csv_reader)
            
            if not items_data:
                return None, "CSV file is empty"
            
            # Validate that all referenced images exist
            image_files = zip_obj.namelist()
            for item in items_data:
                image_file = item.get('image_file', '').strip()
                if not image_file:
                    return None, "CSV has items without image_file specified"
                
                if f"images/{image_file}" not in image_files:
                    return None, f"Image file referenced in CSV but not found in ZIP: {image_file}"
            
            # Create quiz
            quiz = Quiz(
                admin_id=admin_id,
                title=metadata.get('title', 'Imported Quiz'),
                description=metadata.get('description', ''),
                num_positions=int(metadata.get('num_positions', 4))
            )
            db.session.add(quiz)
            db.session.flush()  # Get quiz_id
            
            # Import items with images
            for item_data in items_data:
                image_file = item_data.get('image_file', '').strip()
                
                # Extract and save image
                with zip_obj.open(f"images/{image_file}") as img_source:
                    # Generate unique filename
                    name, ext = os.path.splitext(image_file)
                    unique_filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{name}{ext}"
                    
                    # Upload to GCS or local storage
                    image_content = img_source.read()
                    image_url = upload_file_to_gcs(image_content, unique_filename)
                
                # Create quiz item
                quiz_item = QuizItem(
                    quiz_id=quiz.quiz_id,
                    text=item_data.get('text', '') or '',
                    image_url=image_url,
                    original_filename=image_file,
                    correct_position=int(item_data.get('correct_position', 1)),
                    item_order=int(item_data.get('item_order', 1))
                )
                db.session.add(quiz_item)
            
            db.session.commit()
            return quiz.quiz_id, None
    
    except zipfile.BadZipFile:
        return None, "Invalid ZIP file"
    except KeyError as e:
        return None, f"Missing required field in CSV: {str(e)}"
    except ValueError as e:
        return None, f"Invalid data format: {str(e)}"
    except Exception as e:
        db.session.rollback()
        return None, f"Import failed: {str(e)}"


# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/login')
def admin_login():
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin/create-quiz')
def create_quiz_page():
    return render_template('create_quiz.html')

@app.route('/game/join')
def join_game_page():
    return render_template('join_game.html')

@app.route('/game/play/<game_code>')
def play_game(game_code):
    return render_template('play_game.html', game_code=game_code)

@app.route('/admin/host/<game_code>')
def host_game(game_code):
    return render_template('host_game.html', game_code=game_code)

# API Routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    
    # Check if email already exists
    if Admin.query.filter_by(email=data['email'].lower()).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    # Create new admin
    hashed_password = generate_password_hash(data['password'])
    new_admin = Admin(
        username=data['username'],
        email=data['email'].lower(),
        password_hash=hashed_password
    )
    
    db.session.add(new_admin)
    db.session.commit()
    
    return jsonify({
        'message': 'Registration successful',
        'admin_id': new_admin.admin_id
    }), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data['email'].lower()
    admin = Admin.query.filter_by(email=email).first()
    
    if admin and check_password_hash(admin.password_hash, data['password']):
        return jsonify({
            'message': 'Login successful',
            'admin_id': admin.admin_id,
            'username': admin.username,
            'email': admin.email
        }), 200
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/change-password', methods=['POST'])
def change_password():
    data = request.json
    admin_id = data.get('admin_id')
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not admin_id or not current_password or not new_password:
        return jsonify({'error': 'Missing required fields'}), 400
    
    admin = Admin.query.filter_by(admin_id=admin_id).first()
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    
    # Verify current password
    if not check_password_hash(admin.password_hash, current_password):
        return jsonify({'error': 'Current password is incorrect'}), 401
    
    # Update password
    admin.password_hash = generate_password_hash(new_password)
    db.session.commit()
    
    return jsonify({'message': 'Password changed successfully'}), 200

@app.route('/api/quiz', methods=['POST'])
def create_quiz():
    data = request.json
    
    new_quiz = Quiz(
        admin_id=data['admin_id'],
        title=data['title'],
        description=data.get('description', ''),
        num_positions=data.get('num_positions', 4),
        layout_style=data.get('layout_style', 'grid')
    )
    
    db.session.add(new_quiz)
    db.session.commit()
    
    return jsonify({
        'message': 'Quiz created successfully',
        'quiz_id': new_quiz.quiz_id
    }), 201

@app.route('/api/quiz/<int:quiz_id>/item', methods=['POST'])
def add_quiz_item(quiz_id):
    data = request.form
    
    # Handle file upload
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400
    
    # Save file to GCS or local storage
    filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
    image_content = file.read()
    image_url = upload_file_to_gcs(image_content, filename)
    
    new_item = QuizItem(
        quiz_id=quiz_id,
        text=data.get('text', ''),
        image_url=image_url,
        correct_position=int(data.get('correct_position')),
        item_order=int(data.get('item_order', 1))
    )
    
    db.session.add(new_item)
    db.session.commit()
    
    return jsonify({
        'message': 'Quiz item added successfully',
        'item_id': new_item.item_id
    }), 201

@app.route('/api/quiz/<int:quiz_id>', methods=['GET'])
def get_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404
    
    items = QuizItem.query.filter_by(quiz_id=quiz_id).order_by(QuizItem.item_order).all()
    
    return jsonify({
        'quiz_id': quiz.quiz_id,
        'title': quiz.title,
        'description': quiz.description,
        'num_positions': quiz.num_positions,
        'layout_style': quiz.layout_style,
        'items': [{
            'item_id': item.item_id,
            'text': item.text,
            'image_url': item.image_url,
            'correct_position': item.correct_position,
            'item_order': item.item_order
        } for item in items]
    }), 200

@app.route('/api/admin/<int:admin_id>/quizzes', methods=['GET'])
def get_admin_quizzes(admin_id):
    quizzes = Quiz.query.filter_by(admin_id=admin_id).all()
    
    quiz_list = []
    for quiz in quizzes:
        quiz_list.append({
            'quiz_id': quiz.quiz_id,
            'title': quiz.title,
            'description': quiz.description,
            'created_at': quiz.created_at.strftime('%Y-%m-%d'),
            'item_count': len(quiz.items),
            'num_positions': quiz.num_positions
        })
    
    return jsonify(quiz_list), 200

@app.route('/api/quiz/<int:quiz_id>', methods=['PUT'])
def update_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404
    
    data = request.json
    quiz.title = data.get('title', quiz.title)
    quiz.description = data.get('description', quiz.description)
    quiz.num_positions = data.get('num_positions', quiz.num_positions)
    quiz.layout_style = data.get('layout_style', quiz.layout_style)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Quiz updated successfully',
        'quiz_id': quiz.quiz_id
    }), 200

@app.route('/api/quiz/<int:quiz_id>', methods=['DELETE'])
def delete_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404
    
    db.session.delete(quiz)
    db.session.commit()
    
    return jsonify({'message': 'Quiz deleted successfully'}), 200

@app.route('/api/quiz/item/<int:item_id>', methods=['PUT'])
def update_quiz_item(item_id):
    item = QuizItem.query.get(item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    data = request.form
    
    item.text = data.get('text', item.text)
    item.correct_position = int(data.get('correct_position', item.correct_position))
    item.item_order = int(data.get('item_order', item.item_order))
    
    # Handle image update if provided
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename != '':
            filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
            image_content = file.read()
            image_url = upload_file_to_gcs(image_content, filename)
            item.image_url = image_url
    
    db.session.commit()
    
    return jsonify({
        'message': 'Item updated successfully',
        'item_id': item.item_id
    }), 200

@app.route('/api/quiz/item/<int:item_id>', methods=['DELETE'])
def delete_quiz_item(item_id):
    item = QuizItem.query.get(item_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    db.session.delete(item)
    db.session.commit()
    
    return jsonify({'message': 'Item deleted successfully'}), 200

@app.route('/api/quiz/<int:quiz_id>/export', methods=['GET'])
def export_quiz(quiz_id):
    """Export quiz with images as ZIP file"""
    admin_id = request.args.get('admin_id', type=int)
    
    if not admin_id:
        return jsonify({'error': 'admin_id required'}), 400
    
    zip_buffer, error = export_quiz_to_zip(quiz_id, admin_id)
    
    if error:
        return jsonify({'error': error}), 404
    
    # Get quiz title for filename
    quiz = Quiz.query.get(quiz_id)
    filename = f"{quiz.title.replace(' ', '_')}_export.zip"
    
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/quiz/import', methods=['POST'])
def import_quiz():
    """Import quiz from ZIP file with images"""
    admin_id = request.form.get('admin_id', type=int)
    
    if not admin_id:
        return jsonify({'error': 'admin_id required'}), 400
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.zip'):
        return jsonify({'error': 'File must be a ZIP file'}), 400
    
    quiz_id, error = import_quiz_from_zip(file, admin_id)
    
    if error:
        return jsonify({'error': error}), 400
    
    return jsonify({
        'message': 'Quiz imported successfully',
        'quiz_id': quiz_id
    }), 201

@app.route('/api/game/start', methods=['POST'])
def start_game():
    data = request.json
    quiz_id = data['quiz_id']
    admin_id = data['admin_id']
    
    game_code = generate_game_code()
    
    new_game = GameSession(
        quiz_id=quiz_id,
        admin_id=admin_id,
        game_code=game_code,
        status='waiting'
    )
    
    db.session.add(new_game)
    db.session.commit()
    
    return jsonify({
        'message': 'Game started successfully',
        'game_code': game_code,
        'game_session_id': new_game.game_session_id
    }), 201

@app.route('/api/game/join', methods=['POST'])
def join_game():
    data = request.json
    game_code = data['game_code'].upper()
    nickname = data['nickname']
    
    game = GameSession.query.filter_by(game_code=game_code).first()
    
    if not game:
        return jsonify({'error': 'Game not found'}), 404
    
    if game.status == 'completed':
        return jsonify({'error': 'Game has ended'}), 400
    
    new_participant = Participant(
        game_session_id=game.game_session_id,
        nickname=nickname
    )
    
    db.session.add(new_participant)
    db.session.commit()
    
    return jsonify({
        'message': 'Joined game successfully',
        'participant_id': new_participant.participant_id,
        'game_session_id': game.game_session_id
    }), 200

# SocketIO events
@socketio.on('join_game')
def handle_join_game(data):
    game_code = data['game_code']
    nickname = data['nickname']
    participant_id = data.get('participant_id')
    
    join_room(f'game_{game_code}')
    
    emit('participant_joined', {
        'nickname': nickname,
        'participant_id': participant_id
    }, room=f'host_{game_code}')

@socketio.on('join_host_room')
def handle_join_host_room(data):
    game_code = data['game_code']
    join_room(f'host_{game_code}')
    join_room(f'game_{game_code}')

@socketio.on('start_game')
def handle_start_game(data):
    game_code = data['game_code']
    
    game = GameSession.query.filter_by(game_code=game_code).first()
    if game:
        game.status = 'active'
        db.session.commit()
        
        quiz = Quiz.query.get(game.quiz_id)
        items = QuizItem.query.filter_by(quiz_id=quiz.quiz_id).order_by(QuizItem.item_order).all()
        
        emit('game_started', {
            'quiz': {
                'title': quiz.title,
                'description': quiz.description,
                'num_positions': quiz.num_positions,
                'layout_style': quiz.layout_style,
                'items': [{
                    'item_id': item.item_id,
                    'text': item.text,
                    'image_url': item.image_url,
                    'item_order': item.item_order,
                    'correct_position': item.correct_position
                } for item in items]
            }
        }, room=f'game_{game_code}')

@socketio.on('submit_answer')
def handle_submit_answer(data):
    participant_id = data['participant_id']
    answers = data['answers']  # {item_id: position}
    
    participant = Participant.query.get(participant_id)
    if not participant:
        return
    
    game = GameSession.query.get(participant.game_session_id)
    quiz = Quiz.query.get(game.quiz_id)
    
    # Calculate score
    correct_count = 0
    total_items = len(answers)
    
    for item_id, position in answers.items():
        item = QuizItem.query.get(int(item_id))
        if item and item.correct_position == position:
            correct_count += 1
            
            # Save answer
            answer = ParticipantAnswer(
                participant_id=participant_id,
                item_id=item_id,
                given_position=position,
                is_correct=True
            )
            db.session.add(answer)
    
    # Update participant score
    points_earned = int((correct_count / total_items) * 1000) if total_items > 0 else 0
    participant.total_score = points_earned
    db.session.commit()
    
    emit('answer_result', {
        'correct_count': correct_count,
        'total_items': total_items,
        'points_earned': points_earned
    }, room=request.sid)

@socketio.on('get_results')
def handle_get_results(data):
    game_code = data['game_code']
    
    game = GameSession.query.filter_by(game_code=game_code).first()
    if not game:
        return
    
    participants = Participant.query.filter_by(game_session_id=game.game_session_id)\
        .order_by(Participant.total_score.desc()).all()
    
    leaderboard = [{
        'nickname': p.nickname,
        'score': p.total_score,
        'rank': idx + 1
    } for idx, p in enumerate(participants)]
    
    emit('results_ready', {
        'leaderboard': leaderboard
    }, room=f'game_{game_code}')

@socketio.on('end_game')
def handle_end_game(data):
    game_code = data['game_code']
    
    game = GameSession.query.filter_by(game_code=game_code).first()
    if game:
        game.status = 'completed'
        db.session.commit()
        
        emit('game_ended', {}, room=f'game_{game_code}')

if __name__ == '__main__':
    # Initialize database only once
    init_db()
    
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_ENV') != 'production'
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)
