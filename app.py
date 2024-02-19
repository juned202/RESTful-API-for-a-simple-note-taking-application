from functools import wraps
from flask import Flask
from flask import request
from flask import Flask, request, jsonify
from model import Note, db
from model import User
import jwt
import datetime

from datetime import datetime
app = Flask(__name__)
app.config['SECRET_KEY'] = '123456' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)


# JWT token functions
def generate_token(user_id):
    return jwt.encode({'user_id': user_id}, app.config['SECRET_KEY'], algorithm='HS256')

def verify_token(token):
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        print(payload['user_id'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Invalid token

# Authentication decorator
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Unauthorized'}), 401

        user_id = verify_token(token)
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401

        # Add user ID to the request context for later use
        request.user_id = user_id

        return f(*args, **kwargs)
    return decorated


@app.before_request
def create_tables():
    # The following line will remove this handler, making it
    # only run on the first request
    app.before_request_funcs[None].remove(create_tables)

    db.create_all()


@app.route('/login', methods=['POST'])
def login():
    # Extract data from the request
    data = request.json
    username= data.get('username')
    password = data.get('password')

    # Validate input data
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    # # Check if the user exists (by username or email)
    user = User.query.filter((User.username == username)).first()

    print(user.password)
    if not user :
        if (user.password != password):
            return jsonify({'error': 'Invalid username or password'}), 401


    token = generate_token(user.id)
    return jsonify({'token': token,'message': 'Successfully logged In',"User_ID": user.id}), 200


# Define the /signup endpoint
@app.route('/signup', methods=['POST'])
def signup():
    # Extract data from the request
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # Validate input data
    if not username or not email or not password:
        return jsonify({'error': 'Username, email, and password are required'}), 400

    # Check if username or email is already taken
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already taken'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    # Create a new user record
    new_user = User(username=username, email=email, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User created successfully'}), 201


@app.route('/notes/create', methods=['POST'])
@requires_auth
def create_note():
    # Extract data from the request
    data = request.json
    title = data.get('title')
    content = data.get('content')
    id = data.get('user_id')

    # Validate input data
    if not title or not content:
        return jsonify({'error': 'Title and content are required'}), 400

    # Create a new note object
    new_note = Note(title=title, content=content,user_id=id)

    # Save the new note object to the database
    db.session.add(new_note)
    db.session.commit()

    return jsonify({'message': 'Note created successfully'}), 201

# Route for getting a note by ID
@app.route('/notes/<int:note_id>', methods=['GET'])
@requires_auth
def get_note(note_id):
    # Retrieve the note from the database based on the provided ID
    note = Note.query.get(note_id)
    
    # Check if the note exists
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    
    # Check if the authenticated user is the owner of the note or has been shared the note
    if note.user_id != request.user_id and request.user_id not in [shared_user.id for shared_user in note.shared_users]:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Parse the version history of the note
    version_history = []
    for change in note.content.split('\n\nUpdated at '):
        lines = change.strip().split('\n')
        if len(lines) >= 3:
            timestamp = lines[0]
            print(lines)
            user = lines[2]
            changes = lines[1]
            version_history.append({'timestamp': timestamp, 'user': user, 'changes': changes})
        else:
             timestamp = lines[0]
             version_history.append({'timestamp': timestamp, 'user': request.user_id, 'changes': note.content})
            
    # Return the note content if the user is authorized
    return jsonify({'message': 'Note retrieved successfully', 'title': note.title, 'content': version_history[-1]['changes']}), 200

@app.route('/notes/share', methods=['POST'])
@requires_auth
def share_note():
    # Parse the request body
    data = request.json
    note_id = data.get('note_id')
    user_ids_to_share = data.get('users_to_share')

    # Check if note_id and users_to_share are provided
    if not note_id or not user_ids_to_share:
        return jsonify({'error': 'Note ID and users to share are required'}), 400

    # Retrieve the note from the database based on the provided note ID
    note = Note.query.get(note_id)

    # Check if the note exists
    if not note:
        return jsonify({'error': 'Note not found'}), 404

    # Check if the authenticated user is the owner of the note
    if note.user_id != request.user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    # Retrieve user objects based on the provided user IDs
    users_to_share = User.query.filter(User.id.in_(user_ids_to_share)).all()

    # Add the specified users to the list of shared users for the note
    note.shared_users.extend(users_to_share)

    # Save the changes to the database
    db.session.commit()

    # Return a success message with the appropriate status code
    return jsonify({'message': 'Note shared successfully'}), 200



@app.route('/notes/<int:note_id>', methods=['PUT'])
@requires_auth
def update_note(note_id):
    # Parse the request body
    data = request.json
    updated_content = data.get('updated_content')

    # Check if updated_content is provided
    if not updated_content:
        return jsonify({'error': 'Updated content is required'}), 400

    # Retrieve the note from the database based on the provided note ID
    note = Note.query.get(note_id)

    # Check if the note exists
    if not note:
        return jsonify({'error': 'Note not found'}), 404

    # Check if the authenticated user is either the owner of the note or a shared user
    if note.user_id != request.user_id and request.user_id not in [shared_user.id for shared_user in note.shared_users]:
        return jsonify({'error': 'Unauthorized'}), 403

    # Update the note content with the new content and track the update with a timestamp
    current_time = datetime.utcnow()
    note.content += f'\n\nUpdated at {current_time}:\n{updated_content}:\n{request.user_id}'

    # Save the changes to the database
    db.session.commit()

    # Return a success message with the appropriate status code
    return jsonify({'message': 'Note updated successfully'}), 200


@app.route('/notes/version-history/<int:note_id>', methods=['GET'])
@requires_auth
def get_version_history(note_id):
    # Retrieve the note from the database based on the provided note ID
    note = Note.query.get(note_id)

    # Check if the note exists
    if not note:
        return jsonify({'error': 'Note not found'}), 404

    # Check if the authenticated user is either the owner of the note or a shared user
    if note.user_id != request.user_id and request.user_id not in [shared_user.id for shared_user in note.shared_users]:
        return jsonify({'error': 'Unauthorized'}), 403

    # Parse the version history of the note
    version_history = []
    for change in note.content.split('\n\nUpdated at '):
        lines = change.strip().split('\n')
        if len(lines) >= 2:
            timestamp = lines[0]
            print(lines)
            user = lines[2]
            changes = lines[1]
            version_history.append({'timestamp': timestamp, 'user': user, 'changes': changes})

    # Return the version history as a response
    return jsonify({'version_history': version_history}), 200

if __name__ == "__main__":
    app.run(debug=True)