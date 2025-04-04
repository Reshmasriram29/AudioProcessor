// Configuration
const OPENAI_ENDPOINT = 'wss://api.openai.com/v1/audio/transcriptions';

// DOM Elements
const startButton = document.getElementById('startButton');
const stopButton = document.getElementById('stopButton');
const statusDiv = document.getElementById('status');
const transcriptionText = document.getElementById('transcriptionText');
const responseText = document.getElementById('responseText');

// WebRTC and Audio Variables
let mediaStream;
let peerConnection;
let audioContext;
let mediaRecorder;
let audioChunks = [];

// Initialize WebRTC connection
async function initializeWebRTC() {
    try {
        // Get user media
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // Create audio context
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioContext.createMediaStreamSource(mediaStream);
        
        // Create peer connection
        peerConnection = new RTCPeerConnection({
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' }
            ]
        });

        // Add audio track to peer connection
        mediaStream.getTracks().forEach(track => {
            peerConnection.addTrack(track, mediaStream);
        });

        // Handle ICE candidates
        peerConnection.onicecandidate = event => {
            if (event.candidate) {
                // Send ICE candidate to OpenAI API
                sendIceCandidate(event.candidate);
            }
        };

        // Handle incoming audio
        peerConnection.ontrack = event => {
            const audio = new Audio();
            audio.srcObject = event.streams[0];
            audio.play();
        };

        // Create and send offer
        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);
        
        // Send offer to OpenAI API
        await sendOffer(offer);

        updateStatus('WebRTC connection established');
    } catch (error) {
        console.error('Error initializing WebRTC:', error);
        updateStatus('Error: ' + error.message);
    }
}

// Send offer to OpenAI API
async function sendOffer(offer) {
    try {
        const response = await fetch('/api/offer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ offer })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const answer = await response.json();
        await peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
    } catch (error) {
        console.error('Error sending offer:', error);
        updateStatus('Error sending offer: ' + error.message);
    }
}

// Send ICE candidate to OpenAI API
async function sendIceCandidate(candidate) {
    try {
        const response = await fetch('/api/ice-candidate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ candidate })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
    } catch (error) {
        console.error('Error sending ICE candidate:', error);
    }
}

// Start recording
async function startRecording() {
    try {
        await initializeWebRTC();
        
        mediaRecorder = new MediaRecorder(mediaStream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            await processAudio(audioBlob);
        };
        
        mediaRecorder.start();
        startButton.disabled = true;
        stopButton.disabled = false;
        updateStatus('Recording...', 'recording');
    } catch (error) {
        console.error('Error starting recording:', error);
        updateStatus('Error: ' + error.message);
    }
}

// Stop recording
function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        startButton.disabled = false;
        stopButton.disabled = true;
        updateStatus('Processing audio...');
    }
}

// Process audio and get transcription
async function processAudio(audioBlob) {
    try {
        updateStatus('Processing audio...');
        
        const formData = new FormData();
        formData.append('file', audioBlob, 'audio.wav');
        
        // Add retry logic
        let retries = 3;
        let lastError = null;
        
        while (retries > 0) {
            try {
                const response = await fetch('/api/transcribe', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                if (!data.text) {
                    throw new Error('No transcription received');
                }
                
                const transcription = data.text;
                transcriptionText.textContent = transcription;
                
                if (transcription.trim() === '') {
                    throw new Error('Empty transcription received');
                }
                
                await processQuery(transcription);
                return; // Success, exit the retry loop
            } catch (error) {
                lastError = error;
                retries--;
                if (retries > 0) {
                    updateStatus(`Retrying... (${retries} attempts left)`);
                    await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second before retry
                }
            }
        }
        
        // If we get here, all retries failed
        throw lastError;
        
    } catch (error) {
        console.error('Error processing audio:', error);
        updateStatus('Error: ' + error.message);
        responseText.textContent = 'Error processing audio. Please try again.';
    }
}

// Process the transcribed query
async function processQuery(query) {
    try {
        console.log("Processing query:", query);
        updateStatus("Processing your query...");
        
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query })
        });
        
        console.log("Received response status:", response.status);
        
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        
        await handleResponse(response);
    } catch (error) {
        console.error("Error processing query:", error);
        updateStatus(`Error: ${error.message}`);
    }
}

async function handleResponse(response) {
    try {
        console.log("Starting to handle response...");
        
        const data = await response.json();
        console.log("Response data:", data);
        
        if (data.error) {
            console.error("Error in response:", data.error);
            updateStatus(`Error: ${data.error}`);
            return;
        }
        
        if (!data.text) {
            console.error("No text in response");
            updateStatus("No text response received");
            return;
        }
        
        console.log("Updating status with text response");
        updateStatus(data.text);
        
        if (data.audio) {
            console.log("Processing audio response...");
            try {
                const audioBlob = base64ToBlob(data.audio, 'audio/mp3');
                const audioUrl = URL.createObjectURL(audioBlob);
                const audio = new Audio(audioUrl);
                
                audio.onplay = () => {
                    console.log("Audio started playing");
                    updateStatus("Playing audio response...");
                };
                
                audio.onended = () => {
                    console.log("Audio finished playing");
                    updateStatus("Audio playback completed");
                    URL.revokeObjectURL(audioUrl);
                };
                
                audio.onerror = (error) => {
                    console.error("Audio playback error:", error);
                    updateStatus("Error playing audio response");
                    URL.revokeObjectURL(audioUrl);
                };
                
                console.log("Starting audio playback");
                await audio.play();
            } catch (error) {
                console.error("Error handling audio:", error);
                updateStatus("Error playing audio response");
            }
        } else {
            console.log("No audio in response");
        }
    } catch (error) {
        console.error("Error handling response:", error);
        updateStatus(`Error: ${error.message}`);
    }
}

function base64ToBlob(base64, type) {
    const binaryString = window.atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    return new Blob([bytes], { type: type });
}

// Update status display
function updateStatus(message, className = '') {
    statusDiv.textContent = message;
    statusDiv.className = `status ${className}`;
}

// Event Listeners
startButton.addEventListener('click', startRecording);
stopButton.addEventListener('click', stopRecording); 