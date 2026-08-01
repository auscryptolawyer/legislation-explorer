import pytest
from fastapi.testclient import TestClient
from dotenv import load_dotenv
import os

# Load environment variables for testing purposes
load_dotenv()

# .env has AZURE_CLIENT_ID set, which would cause main.py to
# import SSO auth modules (authlib, etc.) that may not be installed.
os.environ.pop("AZURE_CLIENT_ID", None)
os.environ.pop("AZURE_TENANT_ID", None)
os.environ.pop("AZURE_CLIENT_SECRET", None)

from backend.main import app
from backend import config

client = TestClient(app)

# Test GET /health
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

# Test GET /api/acts returns a list
def test_list_acts():
    # Ensure token is not set for this general test
    original_bearer_token = config.BEARER_TOKEN
    config.BEARER_TOKEN = None
    
    response = client.get("/api/acts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0
    # Check for presence of 'itaa-1997'
    act_ids = [act["id"] for act in response.json()]
    assert "itaa-1997" in act_ids
    
    # Restore original token
    config.BEARER_TOKEN = original_bearer_token

# Test GET /api/tree/itaa-1997 returns a tree structure
def test_get_itaa_1997_tree():
    original_bearer_token = config.BEARER_TOKEN
    config.BEARER_TOKEN = None

    response = client.get("/api/tree/itaa-1997")
    assert response.status_code == 200
    json_response = response.json()
    assert "act" in json_response
    assert "ITAA" in json_response["act"].upper() or "Income Tax" in json_response["act"]
    assert "parts" in json_response
    assert isinstance(json_response["parts"], list)
    assert len(json_response["parts"]) > 0
    
    config.BEARER_TOKEN = original_bearer_token

# Test GET /api/section/itaa-1997/6-5 returns frontmatter and body
def test_get_itaa_1997_section_6_5():
    original_bearer_token = config.BEARER_TOKEN
    config.BEARER_TOKEN = None

    response = client.get("/api/section/itaa-1997/6-5")
    assert response.status_code == 200
    json_response = response.json()
    assert "frontmatter" in json_response
    assert "body" in json_response
    # The exact string changes due to automatic linking, so check for a stable part.
    assert "Income according to ordinary concepts" in json_response["body"]
    assert "ordinary income" in json_response["body"]
    
    config.BEARER_TOKEN = original_bearer_token

# Test that missing section returns 404
def test_get_missing_section_404():
    original_bearer_token = config.BEARER_TOKEN
    config.BEARER_TOKEN = None

    response = client.get("/api/section/itaa-1997/non-existent-section")
    assert response.status_code == 404
    assert response.json() == {"detail": "Section non-existent-section not found"}
    
    config.BEARER_TOKEN = original_bearer_token

# Test GET /api/search?q=income returns results
def test_search_income():
    original_bearer_token = config.BEARER_TOKEN
    config.BEARER_TOKEN = None

    response = client.get("/api/search?q=income")
    assert response.status_code == 200
    json_response = response.json()
    assert "results" in json_response
    assert isinstance(json_response["results"], list)
    assert len(json_response["results"]) > 0
    assert "total" in json_response
    assert json_response["total"] > 0
    
    config.BEARER_TOKEN = original_bearer_token

# Test auth middleware: a request to /api/acts without a valid bearer token should return 401 when BEARER_TOKEN is set.
def test_auth_middleware_unauthorized():
    original_bearer_token = config.BEARER_TOKEN
    config.BEARER_TOKEN = "testtoken123"

    response = client.get("/api/acts")
    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}
    
    config.BEARER_TOKEN = original_bearer_token

def test_auth_middleware_authorized():
    original_bearer_token = config.BEARER_TOKEN
    config.BEARER_TOKEN = "testtoken123"

    headers = {"Authorization": "Bearer testtoken123"}
    response = client.get("/api/acts", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    config.BEARER_TOKEN = original_bearer_token
