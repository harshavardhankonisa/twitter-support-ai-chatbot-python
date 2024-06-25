import json
import os
import time
from dotenv import load_dotenv
from openai import AzureOpenAI
import pymongo
from tenacity import retry, stop_after_attempt, wait_random_exponential

load_dotenv(".env")
DB_CONNECTION_STRING = os.environ.get("DB_CONNECTION_STRING")
AOAI_ENDPOINT = os.environ.get("AOAI_ENDPOINT")
AOAI_KEY = os.environ.get("AOAI_KEY")
AOAI_API_VERSION = "2023-09-01-preview"
COMPLETIONS_DEPLOYMENT = "gpt-4"
EMBEDDINGS_DEPLOYMENT = "text-embedding-ada-002"

db_client = pymongo.MongoClient(DB_CONNECTION_STRING, uuidRepresentation="standard")
db = db_client.customer_support
collection = db.interactions


class CustomerSupportAIAgent:
    """
    Customer Support AI Agent that encapsulates an AI agent that handles customer support inquiries using Azure OpenAI.
    """

    def __init__(self, session_id) -> None:
        self.session_id = session_id
        self.ai_client = AzureOpenAI(
            azure_endpoint=AOAI_ENDPOINT, api_key=AOAI_KEY, api_version=AOAI_API_VERSION
        )
        self.history = []
        pass

    def run(self, prompt: str):
        """
        AI Agent responds to Customer Prompt
        """
        system_prompt = """
        Welcome to Twitter Customer Support! I'm here to assist you with any inquiries related to our services.
        As part of our support team, I'm equipped to answer questions about various aspects of our service offerings. However, please note that my responses are limited to the information available in our support database.
        If you have a question that falls outside of our usual support topics, I may respond with "I don't have that information."
        List of support topics:
        """

        self.history.append({"role": "user", "content": prompt})
        search_results = self.vector_search(prompt)

        # Creating LLM Prompt from search results
        interactions_list = ""
        for result in search_results:
            if "contentVector" in result["document"]:
                del result["document"]["contentVector"]
            interactions_list += (
                json.dumps(result["document"], indent=4, default=str) + "\n\n"
            )
        formatted_prompt = system_prompt + interactions_list

        messages = [
            {"role": "system", "content": formatted_prompt},
            {"role": "user", "content": prompt},
        ]

        completion = self.ai_client.chat.completions.create(
            messages=messages, model=COMPLETIONS_DEPLOYMENT
        )

        self.history.append({"role": "system", "content": formatted_prompt})
        return completion.choices[0].message.content

    def vector_search(self, prompt: str) -> pymongo.command_cursor.CommandCursor:
        """
        Perform a vector search on the specified collection by vectorizing
        the prompt and searching the vector index for the most similar documents.
        returns a list of the top num_results most similar documents
        """
        embed_data = self.generate_embeddings(prompt)
        pipeline = [
            {
                "$search": {
                    "cosmosSearch": {
                        "vector": embed_data,
                        "path": "contentVector",
                        "k": 3,
                    },
                    "returnStoredSource": True,
                }
            },
            {
                "$project": {
                    "similarityScore": {"$meta": "searchScore"},
                    "document": "$$ROOT",
                }
            },
        ]
        results = collection.aggregate(pipeline)
        return results

    @retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
    def generate_embeddings(self, text: str):
        """
        Generate embeddings from string of text using the deployed Azure OpenAI API embeddings model.
        This will be used to vectorize document data and incoming user messages for a similarity search with
        the vector index.
        """
        response = self.ai_client.embeddings.create(
            input=text, model=EMBEDDINGS_DEPLOYMENT
        )
        embeddings = response.data[0].embedding
        time.sleep(0.5)
        return embeddings
