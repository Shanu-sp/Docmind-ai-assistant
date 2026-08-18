import os                                                                                                                                        
    import logging                                                                                                                                   
    from google import genai                                                                                                                         
    from google.genai import types                                                                                                                   
                                                                                                                                                     
    logger = logging.getLogger(__name__)                                                                                                             
                                                                                                                                                     
    # Primary and fallback models for maximum availability                                                                                           
    FALLBACK_MODELS = [                                                                                                                              
        os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),                                                                                          
        "gemini-1.5-flash",                                                                                                                          
        "gemini-2.0-flash",                                                                                                                          
        "gemini-1.5-pro",                                                                                                                            
    ]                                                                                                                                                
                                                                                                                                                     
    class GeminiAIService:                                                                                                                           
        @classmethod                                                                                                                                 
        def get_api_key(cls):                                                                                                                        
            return os.environ.get("GEMINI_API_KEY", "")                                                                                              
                                                                                                                                                     
        @classmethod                                                                                                                                 
        def get_client(cls, api_key=None):                                                                                                           
            key = api_key or cls.get_api_key()                                                                                                       
            if not key:                                                                                                                              
                return None                                                                                                                          
            return genai.Client(api_key=key)                                                                                                         
                                                                                                                                                     
        @classmethod                                                                                                                                 
        def get_config_status(cls):                                                                                                                  
            key = cls.get_api_key()                                                                                                                  
            if not key:                                                                                                                              
                return {"has_api_key": False, "masked_key": None}                                                                                    
            masked = f"***{key[-4:]}" if len(key) >= 4 else "***"                                                                                    
            return {"has_api_key": True, "masked_key": masked}                                                                                       
                                                                                                                                                     
        @classmethod                                                                                                                                 
        def update_api_key(cls, new_key):                                                                                                            
            if not new_key or not new_key.strip():                                                                                                   
                return False, "API key cannot be empty."                                                                                             
            try:                                                                                                                                     
                client = genai.Client(api_key=new_key.strip())                                                                                       
                client.models.generate_content(model="gemini-1.5-flash", contents="ping")                                                            
                os.environ["GEMINI_API_KEY"] = new_key.strip()                                                                                       
                return True, "API Key successfully validated."                                                                                       
            except Exception as e:                                                                                                                   
                return False, f"Invalid API key: {str(e)}"                                                                                           
                                                                                                                                                     
        @classmethod                                                                                                                                 
        def generate_chat_response(cls, system_instruction, chat_history, user_message):                                                             
            client = cls.get_client()                                                                                                                
            if not client:                                                                                                                           
                return "⚠️ AI service is not configured. Please contact the administrator."                                                          
                                                                                                                                                     
            last_error = None                                                                                                                        
            contents = []                                                                                                                            
            for msg in chat_history:                                                                                                                 
                role = "user" if msg.get("role") == "user" else "model"                                                                              
                contents.append(types.Content(                                                                                                       
                    role=role,                                                                                                                       
                    parts=[types.Part.from_text(text=msg.get("content", ""))]                                                                        
                ))                                                                                                                                   
            contents.append(types.Content(                                                                                                           
                role="user",                                                                                                                         
                parts=[types.Part.from_text(text=user_message)]                                                                                      
            ))                                                                                                                                       
                                                                                                                                                     
            for model_name in FALLBACK_MODELS:                                                                                                       
                try:                                                                                                                                 
                    config = types.GenerateContentConfig(                                                                                            
                        system_instruction=system_instruction,                                                                                       
                        temperature=0.7,                                                                                                             
                    )                                                                                                                                
                    response = client.models.generate_content(                                                                                       
                        model=model_name,                                                                                                            
                        contents=contents,                                                                                                           
                        config=config,                                                                                                               
                    )                                                                                                                                
                    if response and response.text:                                                                                                   
                        return response.text.strip()                                                                                                 
                except Exception as e:                                                                                                               
                    err_msg = str(e)                                                                                                                 
                    logger.warning(f"Model {model_name} failed: {err_msg}. Trying fallback...")                                                      
                    last_error = e                                                                                                                   
                    if any(code in err_msg for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "demand"]):                               
                        continue                                                                                                                     
                    else:                                                                                                                            
                        break                                                                                                                        
                                                                                                                                                     
            logger.error(f"All Gemini models exhausted. Final error: {last_error}")                                                                  
            return "⚠️ The AI service is currently experiencing high global traffic. Please wait a few moments and try your question again."         
                                                                                                                                                     
        @classmethod                                                                                                                                 
        def generate_document_summary(cls, document_text, focus=None):                                                                               
            client = cls.get_client()                                                                                                                
            if not client or not document_text:                                                                                                      
                return []                                                                                                                            
                                                                                                                                                     
            prompt = f"Provide 4-6 bullet point executive summary points for this document:\n\n{document_text[:12000]}"                              
            if focus:                                                                                                                                
                prompt += f"\n\nPlease focus the summary specifically on: {focus}"                                                                   
                                                                                                                                                     
            for model_name in FALLBACK_MODELS:                                                                                                       
                try:                                                                                                                                 
                    response = client.models.generate_content(                                                                                       
                        model=model_name,                                                                                                            
                        contents=prompt,                                                                                                             
                        config=types.GenerateContentConfig(                                                                                          
                            system_instruction="You are an expert executive document analyst. Return a clear list of summary bullet points.",        
                            temperature=0.4,                                                                                                         
                        )                                                                                                                            
                    )                                                                                                                                
                    if response and response.text:                                                                                                   
                        lines = [line.strip().lstrip('•-*123456789. ') for line in response.text.strip().split('\n') if line.strip()]                
                        return lines[:6]                                                                                                             
                except Exception as e:                                                                                                               
                    logger.warning(f"Summary with {model_name} failed: {e}. Trying fallback...")                                                     
                    continue                                                                                                                         
                                                                                                                                                     
            return ["Document uploaded successfully. Summary generation temporarily unavailable due to high AI service traffic."]                    
                                                                                                                                                     
        @classmethod                                                                                                                                 
        def generate_suggested_questions(cls, document_text):                                                                                        
            client = cls.get_client()                                                                                                                
            if not client or not document_text:                                                                                                      
                return [                                                                                                                             
                    "What is the main topic of this document?",                                                                                      
                    "Can you summarize the key takeaways?",                                                                                          
                    "What are the important action items?"                                                                                           
                ]                                                                                                                                    
                                                                                                                                                     
            prompt = f"Suggest 3-4 insightful questions a reader might ask about this document:\n\n{document_text[:10000]}"                          
                                                                                                                                                     
            for model_name in FALLBACK_MODELS:                                                                                                       
                try:                                                                                                                                 
                    response = client.models.generate_content(                                                                                       
                        model=model_name,                                                                                                            
                        contents=prompt,                                                                                                             
                        config=types.GenerateContentConfig(                                                                                          
                            system_instruction="Generate 3 concise, highly relevant questions. Return each question on a new line.",                 
                            temperature=0.5,                                                                                                         
                        )                                                                                                                            
                    )                                                                                                                                
                    if response and response.text:
                        questions = [q.strip().lstrip('•-*123456789. ') for q in response.text.strip().split('\n') if q.strip()]
                        return questions[:4]
                except Exception:
                    continue
  
            return [
                "What is the primary conclusion of this document?",
                "Can you explain the main concepts discussed?",
                "What key insights should I know from this text?"
            ]