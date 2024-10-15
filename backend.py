import os
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
from pytube import YouTube
from flask import Flask, request, jsonify
import spacy
from googletrans import Translator

app = Flask(__name__)

# Apply CORS with explicit methods and headers
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})

# Load spaCy NLP model
nlp = spacy.load("en_core_web_sm")
translator = Translator()  # Initialize the Translator

def generate_transcript_from_youtube(video_url):
    try:
        yt = YouTube(video_url)
        video_id = yt.video_id
        
        # Get the available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try to fetch English transcript first
        try:
            transcript = transcript_list.find_transcript(['en'])
        except NoTranscriptFound:
            # If no English transcript, check for Hindi
            try:
                transcript = transcript_list.find_transcript(['hi'])
            except NoTranscriptFound:
                print("No transcripts found for this video.")
                return None
            
        full_transcript = " ".join([entry['text'] for entry in transcript.fetch()])
        return full_transcript.strip()
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

def extract_key_sentences(transcript, num_sentences=5):
    try:
        doc = nlp(transcript)
        sentences = [sent.text for sent in doc.sents if len(sent.text) > 10]
        return sentences[:num_sentences]
    except Exception as e:
        print(f"Error during key sentence extraction: {str(e)}")
        return ["Failed to extract key points"]

def extract_keywords(transcript, num_keywords=10):
    try:
        doc = nlp(transcript)
        keywords = [chunk.text for chunk in doc.noun_chunks]
        return list(set(keywords))[:num_keywords]
    except Exception as e:
        print(f"Error during keyword extraction: {str(e)}")
        return ["Failed to extract keywords"]

def translate_transcript(transcript, dest_language='en'):
    try:
        translated = translator.translate(transcript, dest=dest_language)
        return translated.text
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return transcript  # Return the original transcript if translation fails

@app.route('/generate_transcript', methods=['POST'])
def api_generate_transcript():
    video_url = request.json.get('video_url')
    if not video_url:
        return jsonify({"error": "No video URL provided"}), 400

    transcript = generate_transcript_from_youtube(video_url)
    if transcript:
        # Check if the transcript is in Hindi and translate it
        if "हिंदी" in transcript:  # Basic check; may want to use a more robust method
            translated_transcript = translate_transcript(transcript, dest_language='en')
            transcript = translated_transcript

        key_sentences = extract_key_sentences(transcript)
        keywords = extract_keywords(transcript)
        return jsonify({
            "transcript": transcript,
            "key_sentences": key_sentences,
            "keywords": keywords
        })
    else:
        return jsonify({"error": "Failed to generate transcript. No transcripts available in requested languages."}), 500

# Handle OPTIONS requests explicitly
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
    return response

if __name__ == "__main__":
    app.run(debug=True)
