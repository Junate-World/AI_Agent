import requests
import json
import logging
from typing import Dict, List, Optional, Generator
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT

logger = logging.getLogger(__name__)

class OllamaClient:
    """Client for interacting with local Ollama instance"""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = OLLAMA_TIMEOUT
        
    def check_connection(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            return False
    
    def list_models(self) -> List[str]:
        """List available models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model['name'] for model in models]
            return []
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, 
                temperature: float = 0.7, max_tokens: Optional[int] = None) -> str:
        """Generate a response from the model"""
        try:
            url = f"{self.base_url}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
                
            if max_tokens:
                payload["options"]["num_predict"] = max_tokens
            
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '')
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return f"Error: Unable to generate response - {str(e)}"
    
    def generate_stream(self, prompt: str, system_prompt: Optional[str] = None,
                       temperature: float = 0.7) -> Generator[str, None, None]:
        """Generate a streaming response from the model"""
        try:
            url = f"{self.base_url}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = requests.post(url, json=payload, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if 'response' in data:
                            yield data['response']
                        if data.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"Failed to generate streaming response: {e}")
            yield f"Error: Unable to generate response - {str(e)}"
    
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Chat with the model using message format"""
        try:
            # Convert messages to a single prompt for generate endpoint
            prompt = ""
            for msg in messages:
                if msg['role'] == 'system':
                    prompt += f"System: {msg['content']}\n\n"
                elif msg['role'] == 'assistant':
                    prompt += f"Assistant: {msg['content']}\n\n"
            
            # Use generate endpoint instead of chat for better reliability
            url = f"{self.base_url}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt.strip(),
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }
            
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '')
            
        except Exception as e:
            logger.error(f"Failed to chat: {e}")
            return f"Error: Unable to chat - {str(e)}"
    
    def chat_stream(self, messages: List[Dict[str, str]], 
                   temperature: float = 0.7) -> Generator[str, None, None]:
        """Chat with the model using message format with streaming"""
        try:
            # Convert messages to a single prompt for generate endpoint
            prompt = ""
            for msg in messages:
                if msg['role'] == 'system':
                    prompt += f"System: {msg['content']}\n\n"
                elif msg['role'] == 'user':
                    prompt += f"User: {msg['content']}\n\n"
                elif msg['role'] == 'assistant':
                    prompt += f"Assistant: {msg['content']}\n\n"
            url = f"{self.base_url}/api/chat"
            
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": temperature
                }
            }
            
            response = requests.post(url, json=payload, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if 'message' in data and 'content' in data['message']:
                            yield data['message']['content']
                        if data.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"Failed to chat stream: {e}")
            yield f"Error: Unable to chat - {str(e)}"

# Global client instance
ollama_client = OllamaClient()