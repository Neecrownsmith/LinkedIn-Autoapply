import vertexai
from vertexai.generative_models import GenerativeModel
import os
from dotenv import load_dotenv

load_dotenv()

# Ensure this is your NEW standard GCP Project ID from the console
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = "us-central1"

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Using the Resource ID for the fastest 2.5 Lite model found in your Model Garden
model_id = "gemini-2.5-flash-lite" 
model = GenerativeModel(model_id)

try:
    print(f"Generating content using {model_id} on Vertex AI...")
    response = model.generate_content("Write a short hype tweet about football")
    print("\nSuccess! Response:")
    print(response.text)
except Exception as e:
    print(f"\nError: {e}")
    print("If you see 'Permission Denied', make sure you ran 'gcloud auth application-default login'")
