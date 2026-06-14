import os
try:
    import google.genai as genai
except ImportError:
    import google.generativeai as genai

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
models = genai.list_models()
print([m.name for m in models])
