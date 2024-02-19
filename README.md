
Steps


Create the Database: Run the model.py script to create the database for the application:

!python model.py

Run the Flask Application: Start the Flask application by executing the app.py script:

!python app.py


Import Postman API Collection: Import the provided Postman API collection (notes.postman_api.json) into your Postman application.

Test the APIs: Utilize Postman to test the APIs by sending requests to the various endpoints. Use the following endpoints for different functionalities:

POST /signup: Create a new user account.
POST /login: Authenticate and login a user.
POST /notes/create: Create a new note.
GET /notes/{id}: Retrieve a specific note by its ID.
POST /notes/share: Share a note with other users.
PUT /notes/{id}: Update an existing note.
GET /notes/version-history/{id}: Retrieve the version history of a note.
These steps will guide you through setting up the project, running the Flask application, and testing the APIs using Postman.
