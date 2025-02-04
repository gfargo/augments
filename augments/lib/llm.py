"""
LLM interface module for Ollama integration.
Provides a clean interface for interacting with local language models through Ollama.
"""

import os
import subprocess
from functools import wraps

# Global debug flag from environment
DEBUG_MODE = os.getenv('AUGMENTS_DEBUG', '0').lower() in ('1', 'true', 'yes', 'on')

def debug_output(func):
    """Decorator to conditionally show debug output based on AUGMENTS_DEBUG."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if DEBUG_MODE:
            return func(*args, **kwargs)
    return wrapper
from typing import Dict, List, Optional, Union, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urljoin

try:
    import ollama
    from ollama import AsyncClient, Client, Message, Options
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from .progress import track_progress, LoaderStyle

@debug_output
def debug_env():
    """Print debug information about environment and configuration."""
    env_model = os.getenv('OLLAMA_DEFAULT_MODEL')
    debug_vars = {
        'AUGMENTS_DEBUG': os.getenv('AUGMENTS_DEBUG', '0'),
        'OLLAMA_DEFAULT_MODEL': env_model or 'Not set',
        'PYTHONPATH': os.getenv('PYTHONPATH', 'Not set'),
        'PWD': os.getenv('PWD', 'Not set')
    }
    
    print("\n🔍 Debug Information:")
    print("\nEnvironment Variables:")
    for var, value in debug_vars.items():
        print(f"   • {var}: {value}")
    
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            print("\nAvailable Ollama Models:")
            for line in result.stdout.splitlines():
                if line.strip() and not line.startswith('NAME'):
                    print(f"   • {line}")
        else:
            print(f"\nError running 'ollama list': {result.stderr}")
    except Exception as e:
        print(f"\nError checking ollama: {e}")
    print()

class ModelType(Enum):
    """
    Available model types/sizes.
    Set OLLAMA_DEFAULT_MODEL environment variable to use a specific model.
    """
    SMALL = 'mistral'  # Fast, good for simple tasks
    MEDIUM = 'llama2'  # Good balance of speed and capability
    LARGE = 'llama2:70b'  # More capable but slower
    CODE = 'codellama'  # Specialized for code
    FAST = 'phi'  # Optimized for speed
    
    @classmethod
    def get_default(cls) -> str:
        """
        Get the default model from environment or fallback to MEDIUM.
        
        The model can be specified using:
        1. OLLAMA_DEFAULT_MODEL environment variable
        2. One of the ModelType enum values
        3. Direct model name (e.g., 'llama2:13b')
        """
        model = os.getenv('OLLAMA_DEFAULT_MODEL')
        if model:
            return model
            
        return cls.MEDIUM.value
    
    @classmethod
    def get_description(cls, model: str) -> str:
        """Get description of a model if it's one of the known types."""
        for type_enum in cls:
            if type_enum.value == model:
                return type_enum.__doc__ or "No description available"
        return "Custom model"

# Get default model from environment or fallback
DEFAULT_MODEL = ModelType.get_default()

class Role(Enum):
    """Message role types for chat."""
    SYSTEM = 'system'
    USER = 'user'
    ASSISTANT = 'assistant'

@dataclass
class ChatMessage:
    """Structured chat message."""
    content: str
    role: Role = Role.USER

    def to_dict(self) -> Dict[str, str]:
        """Convert to Ollama message format."""
        return {
            'role': self.role.value,
            'content': self.content
        }

class OllamaClient:
    """
    Client for interacting with Ollama models.
    
    Args:
        model: Default model to use (defaults to env var OLLAMA_DEFAULT_MODEL or 'llama2')
        host: Ollama host address (defaults to http://localhost:11434)
    """
    
    @staticmethod
    def check_ollama_service(host: str = 'http://localhost:11434') -> bool:
        """Check if Ollama service is running and accessible."""
        try:
            import requests
            response = requests.get(urljoin(host, '/api/tags'))
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"\n⚠️  Ollama service not accessible at {host}")
            print("   Make sure Ollama is installed and running:")
            print("   1. Install Ollama: curl https://ollama.ai/install.sh | sh")
            print("   2. Start Ollama: ollama serve")
            print(f"   Error details: {str(e)}\n")
            return False
    
    def __init__(self, model: str = DEFAULT_MODEL, host: str = 'http://localhost:11434'):
        """Initialize Ollama client."""
        if not OLLAMA_AVAILABLE:
            raise ImportError(
                "Ollama Python package not found. Install with: pip install ollama"
            )
        
        # Show debug information if enabled
        debug_env()
        
        self.model = model
        self.host = host
        
        if DEBUG_MODE:
            print(f"\n🔧 Initializing Ollama Client:")
            print(f"   • Host: {host}")
            print(f"   • Model: {model}")
            print(f"   • Default Model: {DEFAULT_MODEL}")
            print()
        
        # First check if Ollama service is running
        if not self.check_ollama_service(host):
            raise ConnectionError("Ollama service is not running or not accessible")
        
        self.client = Client(host=host)
        self._async_client = AsyncClient(host=host)
        
        # Get list of available models directly from ollama command
        try:
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            if result.returncode == 0:
                # Parse model names from ollama list output
                lines = result.stdout.splitlines()[1:]  # Skip header
                model_names = [line.split()[0] for line in lines if line.strip()]
                
                if not model_names:
                    print("\n⚠️  No models found locally. You need to pull a model first:")
                    print(f"   ollama pull {self.model}")
                    raise ConnectionError("No models available")
                
                if self.model not in model_names:
                    print(f"\n⚠️  Model '{self.model}' not found locally.")
                    print("\nAvailable models:")
                    for m in sorted(model_names):
                        print(f"   - {m}")
                    print(f"\n🔄 Pull the requested model with:")
                    print(f"   ollama pull {self.model}")
                    raise ConnectionError(f"Model {self.model} not available")
                
                model_type = ModelType.get_description(self.model)
                print(f"🤖 Using model: {self.model} ({model_type})")
                
            else:
                raise ConnectionError(f"Error listing models: {result.stderr}")
                
        except subprocess.CalledProcessError as e:
            raise ConnectionError(f"Failed to list models: {e}")
        except Exception as e:
            raise ConnectionError(f"Unexpected error checking models: {e}")
    
    def chat(
        self,
        messages: Union[str, List[Union[ChatMessage, Dict]]],
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncGenerator]:
        """
        Chat with the model.
        
        Args:
            messages: Single message string or list of messages
            model: Override default model
            stream: Whether to stream the response
            **kwargs: Additional options to pass to Ollama
        
        Returns:
            Model response text or async generator if streaming
        """
        # Convert single string to message list
        if isinstance(messages, str):
            messages = [ChatMessage(messages)]
        
        # Convert messages to Ollama format
        ollama_messages = []
        for msg in messages:
            if isinstance(msg, ChatMessage):
                ollama_messages.append(msg.to_dict())
            elif isinstance(msg, dict):
                ollama_messages.append(msg)
            else:
                raise ValueError(f"Invalid message format: {type(msg)}")
        
        # Chat with model
        with track_progress(f"Chatting with {model or self.model}", LoaderStyle.PULSE):
            response = self.client.chat(
                model=model or self.model,
                messages=ollama_messages,
                stream=stream,
                **kwargs
            )
            
            if stream:
                return response
            return response.message.content
    
    async def achat(
        self,
        messages: Union[str, List[Union[ChatMessage, Dict]]],
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncGenerator]:
        """Async version of chat method."""
        if isinstance(messages, str):
            messages = [ChatMessage(messages)]
        
        ollama_messages = [
            msg.to_dict() if isinstance(msg, ChatMessage) else msg
            for msg in messages
        ]
        
        with track_progress(f"Chatting with {model or self.model}", LoaderStyle.PULSE):
            response = await self._async_client.chat(
                model=model or self.model,
                messages=ollama_messages,
                stream=stream,
                **kwargs
            )
            
            if stream:
                return response
            return response.message.content
    
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncGenerator]:
        """
        Generate text from a prompt.
        
        Args:
            prompt: Text prompt
            model: Override default model
            stream: Whether to stream the response
            **kwargs: Additional options to pass to Ollama
        
        Returns:
            Generated text or async generator if streaming
        """
        with track_progress(f"Generating with {model or self.model}", LoaderStyle.PULSE):
            response = self.client.generate(
                model=model or self.model,
                prompt=prompt,
                stream=stream,
                **kwargs
            )
            
            if stream:
                return response
            return response.response
    
    async def agenerate(
        self,
        prompt: str,
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncGenerator]:
        """Async version of generate method."""
        with track_progress(f"Generating with {model or self.model}", LoaderStyle.PULSE):
            response = await self._async_client.generate(
                model=model or self.model,
                prompt=prompt,
                stream=stream,
                **kwargs
            )
            
            if stream:
                return response
            return response.response
    
    def embed(
        self,
        input: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs
    ) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for text.
        
        Args:
            input: Text or list of texts to embed
            model: Override default model
            **kwargs: Additional options to pass to Ollama
        
        Returns:
            List of embeddings (or list of lists for batch input)
        """
        with track_progress(f"Generating embeddings with {model or self.model}", LoaderStyle.BRAILLE):
            response = self.client.embeddings(
                model=model or self.model,
                prompt=input,
                **kwargs
            )
            return response.embeddings
    
    async def aembed(
        self,
        input: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs
    ) -> Union[List[float], List[List[float]]]:
        """Async version of embed method."""
        with track_progress(f"Generating embeddings with {model or self.model}", LoaderStyle.BRAILLE):
            response = await self._async_client.embeddings(
                model=model or self.model,
                prompt=input,
                **kwargs
            )
            return response.embeddings
    
    def list_models(self) -> List[Dict]:
        """List available models."""
        with track_progress("Listing models", LoaderStyle.DOTS):
            return self.client.list().models
    
    def pull_model(self, model: str) -> None:
        """
        Pull a model from Ollama.
        
        Args:
            model: Name of model to pull
        """
        with track_progress(f"Pulling model {model}", LoaderStyle.BAR):
            self.client.pull(model)
    
    def create_model(
        self,
        name: str,
        base: str,
        system: Optional[str] = None,
        template: Optional[str] = None
    ) -> None:
        """
        Create a new model from a base model.
        
        Args:
            name: Name for the new model
            base: Base model to derive from
            system: System prompt for the model
            template: Custom prompt template
        """
        with track_progress(f"Creating model {name}", LoaderStyle.MOON):
            self.client.create(
                model=name,
                from_=base,
                system=system,
                template=template
            )
    
    def delete_model(self, model: str) -> None:
        """
        Delete a model.
        
        Args:
            model: Name of model to delete
        """
        with track_progress(f"Deleting model {model}", LoaderStyle.DOTS):
            self.client.delete(model)

# Convenience functions using a default client
_default_client = None

def get_client(model: str = DEFAULT_MODEL) -> OllamaClient:
    """Get or create the default client."""
    global _default_client
    if _default_client is None:
        _default_client = OllamaClient(model=model)
    return _default_client

def chat(*args, **kwargs) -> Union[str, AsyncGenerator]:
    """Convenience function for chatting with default client."""
    return get_client().chat(*args, **kwargs)

def generate(*args, **kwargs) -> Union[str, AsyncGenerator]:
    """Convenience function for generating with default client."""
    return get_client().generate(*args, **kwargs)

def embed(*args, **kwargs) -> Union[List[float], List[List[float]]]:
    """Convenience function for embedding with default client."""
    return get_client().embed(*args, **kwargs)