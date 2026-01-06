from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class Admin(db.Model):
    __tablename__ = 'admin'
    
    admin_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    quizzes = db.relationship('Quiz', backref='admin', lazy=True, cascade='all, delete-orphan')
    game_sessions = db.relationship('GameSession', backref='host', lazy=True)

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    
    quiz_id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.admin_id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    num_positions = db.Column(db.Integer, default=4)  # Number of drop zones (e.g., 1, 2, 3, 4)
    layout_style = db.Column(db.String(20), default='grid')  # 'grid' or 'mindmap'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    items = db.relationship('QuizItem', backref='quiz', lazy=True, cascade='all, delete-orphan')
    game_sessions = db.relationship('GameSession', backref='quiz', lazy=True, cascade='all, delete-orphan')

class QuizItem(db.Model):
    __tablename__ = 'quiz_items'
    
    item_id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.quiz_id'), nullable=False)
    text = db.Column(db.String(255))  # Optional text description
    image_url = db.Column(db.String(500), nullable=False)  # Path to uploaded image
    original_filename = db.Column(db.String(255))  # Original filename from import/export
    correct_position = db.Column(db.Integer, nullable=False)  # Correct position (1, 2, 3, 4, etc.)
    item_order = db.Column(db.Integer, nullable=False)  # Order for display
    
    # Relationships
    participant_answers = db.relationship('ParticipantAnswer', backref='item', lazy=True)

class GameSession(db.Model):
    __tablename__ = 'game_sessions'
    
    game_session_id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.quiz_id'), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.admin_id'), nullable=False)
    game_code = db.Column(db.String(10), unique=True, nullable=False)
    status = db.Column(db.String(20), default='waiting')  # waiting, active, completed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    participants = db.relationship('Participant', backref='game_session', lazy=True, cascade='all, delete-orphan')

class Participant(db.Model):
    __tablename__ = 'participants'
    
    participant_id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey('game_sessions.game_session_id'), nullable=False)
    nickname = db.Column(db.String(50), nullable=False)
    total_score = db.Column(db.Integer, default=0)
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    answers = db.relationship('ParticipantAnswer', backref='participant', lazy=True, cascade='all, delete-orphan')

class ParticipantAnswer(db.Model):
    __tablename__ = 'participant_answers'
    
    participant_answer_id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.participant_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('quiz_items.item_id'), nullable=False)
    given_position = db.Column(db.Integer, nullable=False)  # Position player placed the item
    is_correct = db.Column(db.Boolean, default=False)
    answered_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
