# OpenAI Realtime API with WebRTC Integration

This project demonstrates the integration of OpenAI's Realtime API with WebRTC for real-time audio communication and search functionality, built with FastAPI.

## Features

- Real-time audio communication using WebRTC
- Audio transcription using OpenAI's Whisper API
- Search functionality with fallback to cricket results
- Simple and intuitive web interface
- FastAPI backend with async support
- Automatic API documentation at `/docs`

## Prerequisites

- Python 3.8 or higher
- OpenAI API key
- SerpAPI key (for search functionality)
- Modern web browser with WebRTC support

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file in the project root with the following content:
```
OPENAI_API_KEY=your_openai_api_key
SERPAPI_KEY=your_serpapi_key
```

## Running the Application

1. Start the FastAPI server:
```bash
uvicorn server:app --reload --port 5000
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

3. (Optional) View the automatic API documentation at:
```
http://localhost:5000/docs
```

## Usage

1. Click the "Start Recording" button to begin audio capture
2. Speak your question or query
3. Click "Stop Recording" when finished
4. The application will:
   - Transcribe your audio
   - Search for information from sena.services
   - If sena.services is not accessible, it will search for yesterday's cricket results
   - Display the response in the interface

## Notes

- The application uses WebRTC for real-time audio communication
- Audio is processed using OpenAI's Whisper API for transcription
- Search results are obtained using SerpAPI
- The application will automatically fall back to cricket results if sena.services is not accessible
- FastAPI provides automatic API documentation and validation
- All endpoints are async for better performance

## Troubleshooting

If you encounter any issues:

1. Ensure your API keys are correctly set in the `.env` file
2. Check that your browser supports WebRTC
3. Make sure you have granted microphone permissions to the browser
4. Check the browser console and server logs for error messages
5. Visit the `/docs` endpoint to verify API endpoints are working correctly

## License

This project is licensed under the MIT License - see the LICENSE file for details. 