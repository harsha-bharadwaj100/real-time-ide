import os
from dotenv import load_dotenv
import google.generativeai as genai

print("--- Starting Gemini API Key Test ---")

# 1. Load the .env file
load_dotenv()

# 2. Retrieve the API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("\n❌ ERROR: GEMINI_API_KEY was not found in your .env file.")
else:
    print(f"\nAPI Key found. First 5 chars: {api_key[:5]}...")
    try:
        # 3. Configure the genai library with your key
        genai.configure(api_key=api_key)

        # 4. Attempt to list the available models
        print("Fetching available models from Google...")
        model_list = list(genai.list_models())

        # Filter for models that support the 'generateContent' method
        available_models = [
            m.name
            for m in model_list
            if "generateContent" in m.supported_generation_methods
        ]

        if not available_models:
            print(
                "\n❌ ERROR: Your API key is valid, but no models supporting 'generateContent' were found."
            )
            print("This can happen with new accounts or due to regional restrictions.")
        else:
            print("\n✅ SUCCESS! Your API key is working correctly.")
            print("The following models are available to you:")
            for model_name in available_models:
                print(f"  - {model_name}")

    except Exception as e:
        print(
            f"\n❌ FAILED: An error occurred while trying to connect to the Google API."
        )
        print(f"   Error Details: {e}")

print("\n--- Test Complete ---")
