# Drag & Drop Quiz Platform

A real-time multiplayer drag-and-drop quiz platform built with Flask and Socket.IO.

## Features

- 🧩 **Drag & Drop Interface**: Interactive drag-and-drop gameplay for ordering items
- 📸 **Picture-based Questions**: Upload images to represent steps or items
- 🎮 **Real-time Multiplayer**: Multiple players can join and compete simultaneously
- 🏆 **Live Leaderboard**: See rankings and scores in real-time
- 📊 **Admin Dashboard**: Create and manage quizzes easily
- ⚡ **Instant Feedback**: Players get immediate results after submission

## Use Cases

Perfect for:
- **Educational Games**: Teaching sequences (e.g., steps in a recipe, historical timeline)
- **Training Exercises**: Process ordering, workflow steps
- **Team Building**: Fun competitive activities
- **Assessments**: Test understanding of procedures and sequences

## Quick Start

### 1. Clone & Setup

```bash
cd "Team Management System"
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
```

### 2. Create Upload Folder

```bash
mkdir static\uploads
```

### 3. Run Locally

```bash
python app.py
```

Visit `http://localhost:5000`

## How to Use

### For Admins:

1. **Register/Login** at `/admin/login`
2. **Create a Quiz**:
   - Add a title and description
   - Set the number of positions (e.g., 4 for positions 1-4)
   - Upload images for each item
   - Assign the correct position for each item
3. **Start a Game** from the dashboard
4. **Share the game code** with players
5. **Monitor progress** and view results

### For Players:

1. Go to `/game/join`
2. Enter the **game code** provided by the host
3. Enter your **nickname**
4. Wait for the host to start the game
5. **Drag pictures** into the numbered positions
6. **Submit your answers** when ready
7. See your score and the leaderboard!

## Example Quiz Ideas

- 🍎 **Recipe Steps**: "How to Make Apple Pie" - drag steps in order
- 📚 **Historical Timeline**: Order historical events chronologically
- 🔧 **Assembly Instructions**: Arrange steps to assemble something
- 🌱 **Life Cycles**: Order stages of plant/animal growth
- 🎨 **Process Flows**: Arrange steps in a workflow or procedure

## Configuration

Create a `.env` file for custom configuration:

```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///dragdrop_quiz.db
PORT=5000
```

## Database

The application uses SQLite by default. Database schema includes:
- **Admin**: User accounts for quiz creators
- **Quiz**: Quiz information and settings
- **QuizItem**: Individual items with images and positions
- **GameSession**: Active game sessions
- **Participant**: Players in games
- **ParticipantAnswer**: Player responses and scores

## Technology Stack

- **Backend**: Flask, Flask-SocketIO
- **Database**: SQLAlchemy (SQLite/PostgreSQL)
- **Real-time**: Socket.IO
- **Frontend**: Vanilla JavaScript with HTML5 Drag & Drop API
- **Styling**: CSS3 with gradients and animations

## File Structure

```
.
├── app.py                  # Main Flask application
├── models.py              # Database models
├── requirements.txt       # Python dependencies
├── templates/             # HTML templates
│   ├── index.html        # Home page
│   ├── admin_login.html  # Admin authentication
│   ├── admin_dashboard.html  # Quiz management
│   ├── create_quiz.html  # Quiz creation
│   ├── join_game.html    # Player join page
│   ├── play_game.html    # Drag & drop gameplay
│   └── host_game.html    # Host control panel
└── static/
    └── uploads/          # User-uploaded images
```

## Important Files for Cloning & Running

When you clone this repository, these files are essential:

| File | Purpose |
|------|---------|
| **app.py** | Main Flask application with all routes, Socket.IO events, and business logic |
| **models.py** | SQLAlchemy database models (Admin, Quiz, QuizItem, GameSession, Participant, ParticipantAnswer) |
| **requirements.txt** | Python package dependencies - install with `pip install -r requirements.txt` |
| **templates/** | Jinja2 HTML templates for all pages (login, dashboard, game, etc.) |
| **static/index.html** | Home landing page |
| **Dockerfile** | Container configuration for Docker deployment |
| **cloudbuild.yaml** | Google Cloud Build pipeline configuration |
| **firebase.json** | Firebase hosting configuration |
| **setup-deployment.sh** | Bash script for deployment setup (Linux/Mac) |
| **setup-deployment.bat** | Batch script for deployment setup (Windows) |
| **GCS_SETUP.md** | Guide for setting up Google Cloud Storage integration |
| **GCS_INTEGRATION.md** | Documentation for GCS image upload features |
| **DEPLOYMENT_GUIDE.md** | Complete deployment instructions for various platforms |

**Note:** The following files are ignored by git (see `.gitignore`) as they contain sensitive credentials:
- `.firebase/` - Local Firebase configuration
- `.firebaserc` - Firebase project ID
- `firebase.json` - Firebase config (if not already tracked)
- `static/firebaseConfig.js` - Firebase API keys (you'll need to create this from your Firebase project)

## Tips for Creating Great Quizzes

1. **Use Clear Images**: Make sure images are easy to distinguish
2. **Reasonable Number**: 4-6 items work best for engagement
3. **Logical Sequence**: Ensure there's a clear correct order
4. **Add Descriptions**: Optional text helps clarify items
5. **Test First**: Play through your quiz before sharing

## Deployment

### Heroku:

```bash
heroku create your-app-name
heroku config:set SECRET_KEY=your-secret-key
git push heroku main
```

### Local Network (using ngrok):

```bash
ngrok http 5000
```

Share the public URL with players for demos.

## License

MIT License - Feel free to use and modify!

## Credits

Inspired by interactive quiz platforms like Kahoot, adapted specifically for drag-and-drop ordering activities.
