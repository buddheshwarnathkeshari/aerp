import os
from backend.config.settings import get_settings
from langchain_core.language_models.chat_models import BaseChatModel

settings = get_settings()

def get_llm(temperature=0.0) -> BaseChatModel:
    """Returns a LangChain chat model based on the configured LLM_PROVIDER."""
    provider = settings.llm_provider.lower()
    
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        if not settings.openai_api_key:
            import structlog
            structlog.get_logger().warning("OPENAI_API_KEY is missing! Using mock model fallback.")
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=temperature
        )
        
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        if not settings.anthropic_api_key:
            import structlog
            structlog.get_logger().warning("ANTHROPIC_API_KEY is missing! Using mock model fallback.")
        return ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            temperature=temperature
        )

    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.1"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434"),
            temperature=temperature
        )
        
    else:
        # Default to Gemini
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            api_key=settings.google_api_key,
            temperature=temperature
        )

from langchain_core.embeddings import Embeddings

def get_embedder() -> Embeddings:
    """Returns a LangChain embeddings model based on the configured LLM_PROVIDER."""
    provider = settings.llm_provider.lower()
    
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        if not settings.openai_api_key:
            import structlog
            structlog.get_logger().warning("OPENAI_API_KEY is missing! Using mock model fallback.")
        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.openai_api_key
        )
        
    elif provider == "anthropic":
        # Anthropic doesn't have an embedding model natively available.
        # Fallback to OpenAI if key is present, else Gemini.
        if settings.openai_api_key:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=settings.openai_api_key
            )
        else:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            return GoogleGenerativeAIEmbeddings(
                model=settings.gemini_embedding_model,
                google_api_key=settings.google_api_key
            )

    elif provider == "ollama":
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(
            model=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
        )

    else:
        # Default to Gemini
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embedding_model,
            google_api_key=settings.google_api_key
        )
