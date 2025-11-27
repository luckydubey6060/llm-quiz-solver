# LLM Quiz Solver

Automatic quiz solver using Claude AI and Selenium for the TDS LLM Analysis Quiz project.

## Features

- Solves data analysis quizzes automatically
- Handles JavaScript-rendered pages
- Downloads and processes files (PDF, CSV, etc.)
- Submits answers in correct format
- Handles quiz chains (multiple sequential questions)

## Setup

### Prerequisites

- Python 3.8+
- Chrome browser installed
- Anthropic API key

### Installation

1. Clone this repository:
```bash
git clone https://github.com/luckydubey6060/llm-quiz-solver.git
cd llm-quiz-solver
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file with your credentials:
```bash
ANTHROPIC_API_KEY=your_claude_api_key_here
MY_SECRET=your_secret_here
MY_EMAIL=your_email@example.com
```

### Running Locally
```bash
python app.py
```

API will be available at `http://localhost:5000`

### Testing

Test with demo endpoint:
```bash
curl -X POST http://localhost:5000/quiz \
-H "Content-Type: application/json" \
-d '{
  "email": "your@email.com",
  "secret": "your_secret",
  "url": "https://tds-llm-analysis.s-anand.net/demo"
}'
```

## API Endpoints

### POST /quiz
Accepts quiz requests and solves them.

**Request:**
```json
{
  "email": "your@email.com",
  "secret": "your_secret",
  "url": "https://quiz-url.com"
}
```

**Response:**
```json
{
  "status": "accepted",
  "message": "Quiz solving started"
}
```

### GET /health
Health check endpoint.

## Deployment

Deploy to Render.com, Heroku, or any platform supporting Python web apps.

## License

MIT License - see LICENSE file for details.

update
