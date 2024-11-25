from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote as url_quote
from werkzeug.urls import uri_to_iri
import os
from PIL import Image
from bson import ObjectId
import requests


app = Flask(__name__)
app.secret_key = 'd3c5c64f8e2b0cd6a01f5a7ee02e5e7c'

client = MongoClient('mongodb://localhost:27017/')
db = client['solar_dashboard']
users_collection = db['users']
weather_collection = db['weather']
solar_details_collection = db['solar_details']
vacations_collection = db['vacations']
vehicle_charge_collection = db['vehicle_charge']
profile_settings_collection = db['profile_settings']


def is_authenticated():
    return 'user_id' in session

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('st.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({"message": "No input data provided"}), 400

        existing_user = users_collection.find_one({'username': data['username']})
        if existing_user:
            return jsonify({"message": "You are already registered. Please log in."}), 400

        hashed_password = generate_password_hash(data['password'])
        users_collection.insert_one({'username': data['username'], 'password': hashed_password})
        return jsonify({"success": True})

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No input data provided"}), 400

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"success": False, "message": "Username and password are required"}), 400

        user = users_collection.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            user_id = str(user['_id'])  # Get the user ID from the database
            # Redirect to the profile settings page with the user_id as a query parameter
            return jsonify({"success": True, "redirect": url_for('user_home', user_id=username)})
        else:
            return jsonify({"success": False, "message": "Invalid credentials"}), 401

    return render_template('login.html')


def get_electricity_units(service_number):
    form_url = 'https://tgsouthernpower.org/paybillonline'
    session = requests.Session()
    
    # Initial GET request to load the form page
    initial_response = session.get(form_url)
    
    # Sending POST request with the service number
    payload = {'ukscno': service_number}
    response = session.post(form_url, data=payload)

    # If the response is successful, parse the HTML content
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        td_value_elements = soup.find_all('tr', class_='border-bottom')

        # Extract the unit value from the 6th row
        if len(td_value_elements) >= 6:
            # Extract units (typically in the 6th row, index 5)
            sixth_td_value_element = td_value_elements[5]
            sixth_td_value = sixth_td_value_element.find('td')
            if sixth_td_value:
                units_value = sixth_td_value.text.strip()

            # Extract current month bill (typically in the 8th row, index 7)
            eighth_td_value_element = td_value_elements[7]
            eighth_td_value = eighth_td_value_element.find('td')
            if eighth_td_value:
                bill_value = eighth_td_value.text.strip()
        return units_value, bill_value
    else:
        return f"Failed to retrieve data. Status code: {response.status_code}", None

# Home route to display user data and electricity details
@app.route('/home')
def user_home():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))  # Redirect if the user is not logged in

    # Fetch the user_id from the query parameter
    user_id = request.args.get('user_id')
    if not user_id:
        flash('User ID is missing!', 'warning')
        return redirect(url_for('login'))  # Ensure user_id is passed in the query parameter

    # Fetch electricity details (units and bill) using the username (which is actually the service number)
    units_value, bill_value = get_electricity_units(username)  # Unpack the returned tuple

    # Fetch the user's solar details using the user_id
    solar_details = solar_details_collection.find_one({'user_id': user_id})
    if solar_details:
        installment_cost = solar_details.get('installment_cost', 0)  # Default to 0 if not found
        panels = solar_details.get('panels', 1)  # Default to 1 if not found
    else:
        installment_cost = 0  # Default value if no solar details are found
        panels = 1  # Default value if no solar details are found

    # Get the latest weather data from MongoDB
    latest_weather = weather_collection.find_one(sort=[('timestamp', -1)])  # Fetch the latest weather data
    weather_data = {
        'temperature': latest_weather.get('temperature', 'N/A') if latest_weather else 'Data not available',
        'humidity': latest_weather.get('humidity', 'N/A') if latest_weather else 'Data not available',
        'windSpeed': latest_weather.get('windSpeed', 'N/A') if latest_weather else 'Data not available',
        'cloudCover': latest_weather.get('cloudCover', 'N/A') if latest_weather else 'Data not available',
        'solarRadiation': latest_weather.get('solarRadiation', 'N/A') if latest_weather else 'Data not available',
    }

    # Render the home page with all the relevant data
    return render_template('home.html', 
                           units_value=units_value, 
                           bill_value=bill_value,  # Pass bill_value to the template
                           weather_data=weather_data, 
                           installment_cost=installment_cost, 
                           panels=panels, 
                           user_id=user_id)





@app.route('/solar_details', methods=['GET', 'POST'])
def solar_details():
    # Fetch the user_id from the query parameter
    user_id = request.args.get('user_id')
    if not user_id:
        flash('User ID is missing!', 'warning')
        return redirect(url_for('login'))  # Ensure user_id is passed

    if request.method == 'POST':
        # Retrieve the form data
        total_panels = request.form.get('total_panels')
        setup_date = request.form.get('setup_date')
        installment_cost = request.form.get('installment_cost')

        # Validate the data if necessary
        if not total_panels or not setup_date or not installment_cost:
            flash('All fields are required!', 'danger')
            return redirect(url_for('solar_details', user_id=user_id))

        # Convert setup_date to a datetime object
        try:
            setup_date = datetime.strptime(setup_date, '%Y-%m-%d')
        except ValueError:
            flash('Invalid setup date format!', 'danger')
            return redirect(url_for('solar_details', user_id=user_id))

        # Prepare the data for insertion or update
        solar_details_data = {
            'user_id': user_id,
            'panels': total_panels,
            'initial_setup_date': setup_date,
            'installment_cost': installment_cost,
            'updated_at': datetime.utcnow()  # Save the current time of update
        }

        # Check if the user already has solar details stored
        existing_details = solar_details_collection.find_one({'user_id': user_id})
        
        if existing_details:
            # Update existing document if the user already has solar details
            solar_details_collection.update_one(
                {'user_id': user_id},
                {'$set': solar_details_data}
            )
            flash('Solar details updated successfully!', 'success')
        else:
            # Insert new document if no existing data
            solar_details_collection.insert_one(solar_details_data)
            flash('Solar details saved successfully!', 'success')

        return redirect(url_for('solar_details', user_id=user_id))

    # Fetch existing solar details for the user if any
    solar_details = solar_details_collection.find_one({'user_id': user_id})

    return render_template('solar_details.html', user_id=user_id, solar_details=solar_details)




@app.route('/profile_settings', methods=['GET', 'POST'])
def profile_settings():
    # Get user_id from the query parameter
    user_id = request.args.get('user_id')
    if not user_id:
        flash('User ID is missing!', 'warning')
        return redirect(url_for('login'))  # Redirect to login page if user_id is not passed

    # Fetch user data from the database using user_id
    try:
        user = users_collection.find_one({'_id': ObjectId(user_id)})  # Ensure correct query using ObjectId
    except Exception as e:
        flash(f"Error fetching user data: {e}", 'danger')
        return redirect(url_for('login'))  # Redirect if user not found

    if not user:
        flash('User not found!', 'danger')
        return redirect(url_for('login'))  # Redirect if user not found

    new_password_hashed = None  # To store the new password for debugging/display

    if request.method == 'POST':
        # Get current and new password from the form
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Validate password fields
        if not current_password or not new_password or not confirm_password:
            flash('All fields are required!', 'danger')
            return redirect(url_for('profile_settings', user_id=user_id))

        # Check if the current password matches
        if not check_password_hash(user['password'], current_password):
            flash('Current password is incorrect!', 'danger')
            return redirect(url_for('profile_settings', user_id=user_id))

        # Ensure new password matches the confirmation password
        if new_password != confirm_password:
            flash('New password and confirmation do not match!', 'danger')
            return redirect(url_for('profile_settings', user_id=user_id))

        # Hash the new password
        new_password_hashed = generate_password_hash(new_password)
        print(f"Hashed new password: {new_password_hashed}")  # Debug: Print hashed password to console

        # Update the password in the database for the logged-in user
        try:
            update_result = users_collection.update_one(
                {'_id': ObjectId(user_id)},  # Query by user_id
                {'$set': {'password': new_password_hashed, 'updated_at': datetime.utcnow()}}  # Set new password
            )

            if update_result.modified_count > 0:
                flash('Password changed successfully!', 'success')
            else:
                flash('No changes were made to your password.', 'info')
        except Exception as e:
            flash(f"Error updating password: {e}", 'danger')

        return redirect(url_for('profile_settings', user_id=user_id))  # Redirect back to profile settings

    return render_template('profile_settings.html', user=user, hashed_password=new_password_hashed)



@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/vacations', methods=['GET', 'POST'])
def vacations():
    # Fetch user_id from query parameters
    user_id = request.args.get('user_id')
    if not user_id:
        flash('User ID is missing!', 'warning')
        return redirect(url_for('login'))  # Ensure user_id is passed

    if request.method == 'POST':
        start_date = request.form.get('startDate')
        end_date = request.form.get('endDate')

        # Validate and calculate the number of days
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            days = (end_date_obj - start_date_obj).days
            if days < 0:
                raise ValueError("End date cannot be before start date.")
        except ValueError as e:
            return jsonify({'message': f'Invalid dates provided: {str(e)}'}), 400

        # Insert data into MongoDB with user_id
        vacations_collection.insert_one({
            'user_id': user_id,
            'start_date': start_date,
            'end_date': end_date,
            'days': days,
            'created_at': datetime.utcnow()
        })

        return redirect(url_for('vacations', message='Vacation data stored successfully!', user_id=user_id))  # Pass user_id in the redirect

    # Fetch vacation details for the user from the collection (if any)
    user_vacations = vacations_collection.find({'user_id': user_id})

    return render_template('vacations.html', user_id=user_id, vacations=user_vacations)  # Pass user_id to template

@app.route('/vehicle_charge', methods=['GET', 'POST'])
def vehicle_charge():
    # Fetch user_id from query parameters
    user_id = request.args.get('user_id')
    if not user_id:
        flash('User ID is missing!', 'warning')
        return redirect(url_for('login'))  # Ensure user_id is passed

    if request.method == 'POST':
        capacity = request.form.get('capacity')
        charges_per_month = request.form.get('chargesPerMonth')

        vehicle_charge_collection.insert_one({
            'capacity': capacity,
            'charges_per_month': charges_per_month,
            'user_id': user_id,
            'created_at': datetime.utcnow()
        })

        return redirect(url_for('vehicle_charge', message='Data submitted successfully!', user_id=user_id))  # Pass user_id in the redirect

    return render_template('vehicle_charge.html', user_id=user_id)  # Pass user_id to template

if __name__ == "__main__":
    app.run(debug=True)
