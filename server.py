from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import os
import openai
import requests
from datetime import datetime, timedelta
import json
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv
import tempfile
import base64
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Debug logging for environment variables
print("Checking environment variables...")
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SERPAPI_KEY = os.getenv('SERPAPI_KEY')

print(f"OPENAI_API_KEY exists: {bool(OPENAI_API_KEY)}")
print(f"SERPAPI_KEY exists: {bool(SERPAPI_KEY)}")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

openai.api_key = OPENAI_API_KEY

# Create a temporary directory for audio files
TEMP_DIR = tempfile.gettempdir()

# Pydantic models for request validation
class OfferRequest(BaseModel):
    offer: dict

class IceCandidateRequest(BaseModel):
    candidate: dict

class SearchRequest(BaseModel):
    query: str

app = FastAPI()

# Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
    expose_headers=["*"]
)

# Mount static files
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
async def read_root():
    return FileResponse('index.html')

@app.get("/app.js")
async def read_js():
    return FileResponse('app.js')

@app.post("/api/offer")
async def handle_offer(request: OfferRequest):
    try:
        # Here you would typically forward the offer to OpenAI's WebRTC endpoint
        # For now, we'll return a mock answer
        answer = {
            'type': 'answer',
            'sdp': 'mock-sdp'
        }
        return JSONResponse(content=answer)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/api/ice-candidate")
async def handle_ice_candidate(request: IceCandidateRequest):
    try:
        # Here you would typically forward the ICE candidate to OpenAI's WebRTC endpoint
        return JSONResponse(content={"status": "success"})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        print("Received audio file for transcription")
        
        # Create a unique temporary file path
        temp_path = os.path.join(TEMP_DIR, f"temp_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
        
        try:
            # Save the file to the temporary directory
            with open(temp_path, 'wb') as f:
                content = await file.read()
                if not content:
                    raise ValueError("Empty file received")
                f.write(content)
            print(f"Audio file saved successfully to {temp_path}")
            
            # Check file size
            file_size = os.path.getsize(temp_path)
            if file_size == 0:
                raise ValueError("File is empty")
            print(f"File size: {file_size} bytes")
            
        except Exception as e:
            print(f"Error saving file: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Error saving file: {str(e)}"}
            )
        
        try:
            # Transcribe using OpenAI's Whisper API with the new format
            print("Starting transcription with OpenAI")
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            
            with open(temp_path, 'rb') as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f
                )
            print("Transcription completed successfully")
            
        except Exception as e:
            print(f"Error during transcription: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Error during transcription: {str(e)}"}
            )
        finally:
            # Clean up
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    print("Temporary file removed")
            except Exception as e:
                print(f"Error removing temporary file: {str(e)}")
        
        return JSONResponse(content={"text": transcript.text})
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Unexpected error: {str(e)}"}
        )

@app.post("/api/search")
async def search(request: SearchRequest):
    try:
        query = request.query.lower()  # Convert query to lowercase for easier matching
        print(f"Received query: {query}")
        
        # Check if the query is about cricket
        cricket_keywords = ['cricket', 'sports', 'match', 'game', 'wicket', 'yesterday']
        is_cricket_query = any(keyword in query for keyword in cricket_keywords)
        
        if is_cricket_query:
            print("Detected cricket-related query")
            # Get actual yesterday's date
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%B %d, %Y')
            search_query = f"cricket match results {yesterday} scorecard highlights"
            
            print(f"Searching for cricket results for {yesterday}...")
            # Use SerpAPI to search for cricket results
            params = {
                'api_key': SERPAPI_KEY,
                'q': search_query,
                'engine': 'google',
                'num': 5  # Get more results for better accuracy
            }
            
            try:
                response = requests.get('https://serpapi.com/search', params=params)
                results = response.json()
                
                if 'organic_results' in results and results['organic_results']:
                    # Combine information from multiple results for better coverage
                    cricket_info = []
                    for result in results['organic_results'][:3]:  # Get top 3 results
                        if 'snippet' in result:
                            cricket_info.append(result['snippet'])
                    
                    if cricket_info:
                        response_text = f"Here are the cricket results from {yesterday}:\n\n" + "\n\n".join(cricket_info)
                    else:
                        response_text = f"No detailed cricket results found for {yesterday}. Please try searching for a different date."
                else:
                    response_text = f"No cricket results found for {yesterday}. Please try searching for a different date."
            except Exception as serp_error:
                print(f"Error with SerpAPI: {str(serp_error)}")
                response_text = "Unable to fetch cricket results. Please try again later."
        else:
            # Try to search sena.services for non-cricket queries
            print("Attempting to fetch from sena.services...")
            try:
                response = requests.get('https://sena.services')
                if response.status_code == 200:
                    # Parse the HTML content
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract services from the website
                    services = []
                    
                    # Look for service sections in common HTML patterns
                    service_sections = soup.find_all(['section', 'div'], class_=lambda x: x and ('service' in x.lower() or 'services' in x.lower()))
                    
                    for section in service_sections:
                        # Look for service items
                        service_items = section.find_all(['h2', 'h3', 'li', 'p'])
                        for item in service_items:
                            text = item.get_text(strip=True)
                            if text and len(text) > 10:  # Filter out short texts
                                services.append(text)
                    
                    # If no services found in structured format, try to extract from main content
                    if not services:
                        main_content = soup.find('main') or soup.find('article') or soup.find('body')
                        if main_content:
                            paragraphs = main_content.find_all('p')
                            for p in paragraphs:
                                text = p.get_text(strip=True)
                                if text and len(text) > 20 and ('service' in text.lower() or 'offer' in text.lower()):
                                    services.append(text)
                    
                    # If still no services found, use default list
                    if not services:
                        services = [
                            "Web Development",
                            "Mobile App Development",
                            "Cloud Services",
                            "AI and Machine Learning",
                            "Digital Marketing",
                            "IT Consulting"
                        ]
                    
                    # Format the services list
                    services_list = "\n".join([f"- {service}" for service in services])
                    response_text = f"Sena provides the following services:\n{services_list}\n\nFor more detailed information, please visit https://sena.services directly."
                else:
                    print(f"Failed to fetch sena.services. Status code: {response.status_code}")
                    # If sena.services is not accessible, fall back to cricket results
                    yesterday = (datetime.now() - timedelta(days=1)).strftime('%B %d, %Y')
                    search_query = f"cricket match results {yesterday} scorecard highlights"
                    print(f"Falling back to cricket results for {yesterday}...")
                    params = {
                        'api_key': SERPAPI_KEY,
                        'q': search_query,
                        'engine': 'google',
                        'num': 5
                    }
                    response = requests.get('https://serpapi.com/search', params=params)
                    results = response.json()
                    if 'organic_results' in results and results['organic_results']:
                        cricket_info = []
                        for result in results['organic_results'][:3]:
                            if 'snippet' in result:
                                cricket_info.append(result['snippet'])
                        if cricket_info:
                            response_text = f"Here are the cricket results from {yesterday}:\n\n" + "\n\n".join(cricket_info)
                        else:
                            response_text = "Unable to access sena.services at the moment. Please try again later or visit the website directly."
                    else:
                        response_text = "Unable to access sena.services at the moment. Please try again later or visit the website directly."
            except Exception as e:
                print(f"Error accessing sena.services: {str(e)}")
                response_text = "Unable to access sena.services. Please try again later or visit the website directly."

        # Convert text response to audio using OpenAI's text-to-speech
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            speech_response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=response_text
            )
            
            # Save the audio to a temporary file
            temp_audio_path = os.path.join(TEMP_DIR, f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3")
            speech_response.stream_to_file(temp_audio_path)
            
            # Read the audio file and convert to base64
            with open(temp_audio_path, 'rb') as audio_file:
                audio_data = audio_file.read()
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Clean up the temporary file
            os.remove(temp_audio_path)
            
            return JSONResponse(content={
                "text": response_text,
                "audio": audio_base64
            })
            
        except Exception as e:
            print(f"Error converting text to speech: {str(e)}")
            return JSONResponse(content={
                "text": response_text,
                "error": "Failed to generate audio response"
            })
            
    except Exception as e:
        print(f"Unexpected error in search: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Unexpected error: {str(e)}"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000) 