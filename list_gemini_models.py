#!/usr/bin/env python3
"""
Script to list available Gemini models.
This helps diagnose the "model not found" error.
"""

import os
import google.generativeai as genai
import json

def load_api_key():
    """Load Gemini API key from file."""
    try:
        with open("gemini-api-key", 'r') as f:
            return f.read().strip()
    except Exception as e:
        print(f"⚠️ Error loading Gemini API key: {str(e)}")
        return None

def main():
    # Load and configure API key
    api_key = load_api_key()
    if not api_key:
        print("❌ No API key found")
        return
    
    genai.configure(api_key=api_key)
    
    # Print API version and configuration
    print(f"🔑 API Key: {api_key[:5]}...{api_key[-5:]}")
    print(f"📚 Package Version: {genai.__version__}")
    
    try:
        # List available models
        print("\n📋 Listing available models...")
        models = genai.list_models()
        
        print("\n✅ Available Models:")
        for model in models:
            print(f"- {model.name}: {model.display_name}")
            print(f"  Supported methods: {', '.join(model.supported_generation_methods)}")
            print(f"  Input token limit: {model.input_token_limit}")
            print(f"  Output token limit: {model.output_token_limit}")
            print()
        
    except Exception as e:
        print(f"❌ Error listing models: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {e.args}")

if __name__ == "__main__":
    main()
