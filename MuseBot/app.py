from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import google.generativeai as genai
import os
from werkzeug.utils import secure_filename
from get_file import extract_pdf_text 

# Initialize the Gemini API
api_key = "AIzaSyCcsbHYw327pZ9s5xtxqb3ZH-eWwpLzGG8"
genai.configure(api_key=api_key)
model_pro = genai.GenerativeModel(model_name="gemini-1.5-pro")

app = Flask(__name__)
app.secret_key = 'your_secret_key'

TEMP_DIR = "temp"
UPLOAD_FOLDER = TEMP_DIR

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db_config = {
    'user': 'root',
    'password': 'vansh',
    'host': 'localhost',
    'database': 'hackathon'
}

def get_locations():
    """Fetch distinct locations from the database."""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT location FROM tickets")
        locations = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return locations
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return []

def talk_with_data(text, query, model):
    """Generate a response using the Gemini model based on provided text and query."""
    try:
        response = model.generate_content(f"{text} {query}")
        if response.parts:
            raw_response = response.parts[0].text
            formatted_response = convert_markdown_to_html(raw_response)
            return formatted_response
        else:
            feedback = response.prompt_feedback
            if feedback:
                return f"Prompt feedback: {feedback}"
            else:
                return "No response generated. Please try a different query."
    except Exception as e:
        return f"Error: {str(e)}"

def convert_markdown_to_html(text):
    """Convert markdown text to HTML."""
    import re
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'\~\~(.*?)\~\~', r'<del>\1</del>', text)
    text = re.sub(r'\`([^`]*)\`', r'<code>\1</code>', text)
    text = re.sub(r'\n', '<br>', text)
    return text

def talk_with_pdf(pdf_path, query, model):
    """Handle interaction with the PDF and generate a response."""
    try:
        text = extract_pdf_text(pdf_path)
        if text:
            response = talk_with_data(text, query, model)
            return response
        else:
            return "Failed to extract text from the file."
    except Exception as e:
        return f"Error: {str(e)}"

def search_locations(search_query):
    """Search locations in the database based on the query."""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        query = "SELECT DISTINCT location FROM tickets WHERE location LIKE %s"
        cursor.execute(query, (f"%{search_query}%",))
        locations = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return locations
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return []

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = password  # Implement hashing for security
        
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, hashed_password, 'user'))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('login'))
        except mysql.connector.Error as e:
            return f"An error occurred: {str(e)}"
    
    return render_template('register.html')

@app.route('/', methods=['GET', 'POST'])
def login():
    """User login."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = password  # Implement hashing for security
        
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, hashed_password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            session['username'] = user['username']
            session['role'] = user['role']
            if user['role'] == 'admin':
                return redirect(url_for('admin_page'))
            else:
                return redirect(url_for('user_page'))
        else:
            return "Invalid credentials. Please try again."
    
    return render_template('login.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin_page():
    """Admin page to manage tickets."""
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        location = request.form.get('location')
        tickets_available = request.form.get('tickets_available')
        price = request.form.get('price')
        pdf = request.files.get('pdf')

        if not location or not tickets_available or not price:
            return "Location, available tickets, and price fields are required."

        try:
            # Save file if provided
            pdf_path = None
            if pdf and pdf.filename != '':
                filename = secure_filename(pdf.filename)
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                pdf.save(pdf_path)

            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tickets (location, pdf_path, tickets_available, price) VALUES (%s, %s, %s, %s)",
                           (location, pdf_path, tickets_available, price))
            conn.commit()
            cursor.close()
            conn.close()
            return "Location added successfully!"
        except mysql.connector.Error as e:
            return f"An error occurred: {str(e)}"

    return render_template('admin.html')

@app.route('/user', methods=['GET', 'POST'])
def user_page():
    """User page for interacting with the system."""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        search_query = request.form.get('search_query', '')
        locations = search_locations(search_query)
        
        if 'chatbot-input' in request.form:
            query = request.form['chatbot-input']
            location = request.form['location']
            
            try:
                conn = mysql.connector.connect(**db_config)
                cursor = conn.cursor()
                cursor.execute("SELECT pdf_path FROM tickets WHERE location = %s", (location,))
                result = cursor.fetchone()
                cursor.close()
                conn.close()

                if result:
                    pdf_path = result[0]
                    if pdf_path:
                        response = talk_with_pdf(pdf_path, query, model_pro)
                    else:
                        response = "No file associated with the selected location."
                else:
                    response = "No data found for the selected location."

            except mysql.connector.Error as e:
                response = f"Database error: {e}"

            return render_template('user.html', locations=locations, chatbot_response=response)
        
        elif 'tickets' in request.form:
            username = session['username']
            location = request.form['location']
            tickets_requested = int(request.form['tickets'])

            try:
                conn = mysql.connector.connect(**db_config)
                cursor = conn.cursor()
                cursor.execute("SELECT tickets_available FROM tickets WHERE location = %s", (location,))
                result = cursor.fetchone()

                if result and result[0] >= tickets_requested:
                    new_tickets_available = result[0] - tickets_requested
                    cursor.execute("UPDATE tickets SET tickets_available = %s WHERE location = %s", (new_tickets_available, location))
                    cursor.execute("INSERT INTO bookings (username, location, tickets_booked) VALUES (%s, %s, %s)",
                                   (username, location, tickets_requested))
                    conn.commit()
                    response = "Tickets booked successfully!"
                else:
                    response = "Not enough tickets available."

                cursor.close()
                conn.close()

            except mysql.connector.Error as e:
                response = f"Database error: {e}"

            return render_template('user.html', locations=locations, booking_response=response)
    
    locations = get_locations()
    return render_template('user.html', locations=locations)

@app.route('/logout')
def logout():
    """Logout user."""
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('login'))

@app.route('/check_price', methods=['POST'])
def check_price():
    """Check ticket price based on location."""
    location = request.form['location']
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT price FROM tickets WHERE location = %s", (location,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if result:
        return f"The ticket price for {location} is {result[0]}."
    else:
        return "Location not found."
    
@app.route('/view_tickets')
def view_tickets():
    """View all booked tickets for the logged-in user."""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM bookings WHERE username = %s", (username,))
        tickets = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return render_template('view_tickets.html', tickets=tickets)
    except mysql.connector.Error as e:
        return f"Database error: {e}"


if __name__ == '__main__':
    app.run(debug=True)
