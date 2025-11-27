from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from solver import QuizSolver
import threading
import logging

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Your credentials from .env file
MY_SECRET = os.getenv("MY_SECRET")
MY_EMAIL = os.getenv("MY_EMAIL")

@app.route('/quiz', methods=['POST'])
def quiz_endpoint():
    """
    Main endpoint that receives quiz requests
    This is where the evaluation system will send requests
    """
    try:
        # Get JSON data from request
        data = request.get_json()
        
        # Validate JSON exists
        if not data:
            logger.error("No JSON data received")
            return jsonify({"error": "Invalid JSON"}), 400
        
        # Extract fields
        email = data.get('email')
        secret = data.get('secret')
        url = data.get('url')
        
        logger.info(f"Received request for email: {email}")
        
        # Verify secret matches
        if secret != MY_SECRET:
            logger.error(f"Invalid secret provided")
            return jsonify({"error": "Invalid secret"}), 403
        
        # Validate URL is provided
        if not url:
            logger.error("No URL provided")
            return jsonify({"error": "URL missing"}), 400
        
        logger.info(f"Starting quiz solver for URL: {url}")
        
        # Create solver instance
        solver = QuizSolver(email, secret)
        
        # Start solving in background thread (don't block response)
        thread = threading.Thread(
            target=solver.solve_quiz_chain,
            args=(url,),
            daemon=True
        )
        thread.start()
        
        # Return immediate response
        return jsonify({
            "status": "accepted",
            "message": "Quiz solving started"
        }), 200
        
    except Exception as e:
        logger.error(f"Error in quiz endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint to verify API is running
    """
    return jsonify({
        "status": "healthy",
        "message": "Quiz solver API is running"
    }), 200

@app.route('/', methods=['GET'])
def home():
    """
    Home endpoint with basic info
    """
    return jsonify({
        "name": "LLM Quiz Solver",
        "version": "1.0",
        "endpoints": {
            "POST /quiz": "Submit quiz to solve",
            "GET /health": "Health check"
        }
    }), 200

if __name__ == '__main__':
    # Check if required environment variables are set
    if not MY_SECRET or not MY_EMAIL:
        logger.error("Missing required environment variables!")
        logger.error("Please set MY_SECRET and MY_EMAIL in .env file")
        exit(1)
    
    # Run the Flask app
    logger.info("Starting Flask app...")
    app.run(host='0.0.0.0', port=5001, debug=True)