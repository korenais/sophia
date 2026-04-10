from __future__ import annotations

from typing import Optional, List
from openai import AsyncOpenAI
import os


class OpenAiVectorModel:
    TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"
    TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"
    TEXT_EMBEDDING_ADA_002 = "text-embedding-ada-002"


async def openai_text_to_vector(
    input_text: str,
    model: str = OpenAiVectorModel.TEXT_EMBEDDING_3_LARGE,
    openai_client: Optional[AsyncOpenAI] = None
) -> Optional[List[float]]:
    """
    Convert text to vector using OpenAI embeddings.
    
    Args:
        input_text: Text to vectorize
        model: OpenAI embedding model to use
        openai_client: Optional OpenAI client (will create one if not provided)
    
    Returns:
        List of floats representing the embedding, or None if error
    """
    if not openai_client:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY not found in environment")
            return None
        openai_client = AsyncOpenAI(api_key=api_key)
    
    try:
        response = await openai_client.embeddings.create(
            model=model,
            input=input_text
        )
        return response.data[0].embedding
    except Exception as error:
        print(f"Error fetching OpenAI embedding: {error}")
        return None


async def vectorize_description(
    description: str,
    openai_client: Optional[AsyncOpenAI] = None
) -> Optional[List[float]]:
    """
    Vectorize a user description for matching.
    
    Args:
        description: User's description text
        openai_client: Optional OpenAI client
    
    Returns:
        Embedding vector or None if error
    """
    if not description or len(description.strip()) < 10:
        return None
    
    return await openai_text_to_vector(
        description.strip(),
        OpenAiVectorModel.TEXT_EMBEDDING_3_LARGE,
        openai_client
    )


async def create_default_vector(
    openai_client: Optional[AsyncOpenAI] = None
) -> Optional[List[float]]:
    """
    Create a default/empty vector for new users who don't have a description yet.
    This allows them to be included in matchable_users list and use /my_matches command.
    
    The vector is generated from a minimal description that represents an incomplete profile.
    This will be updated later when the user fills in their actual description.
    
    Args:
        openai_client: Optional OpenAI client
    
    Returns:
        Default embedding vector or None if error
    """
    # Use a minimal description that will be replaced when user fills in their profile
    default_text = "New user profile - profile information will be added later"
    
    try:
        return await openai_text_to_vector(
            default_text,
            OpenAiVectorModel.TEXT_EMBEDDING_3_LARGE,
            openai_client
        )
    except Exception as e:
        print(f"Warning: Failed to create default vector: {e}")
        # Fallback: return a zero vector with standard embedding dimension (3072 for text-embedding-3-large)
        # This ensures the user can still use /my_matches even if OpenAI API fails
        return [0.0] * 3072


