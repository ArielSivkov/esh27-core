import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from backend.api.main import app
import httpx

client = TestClient(app)

def test_create_lead_work_success():
    with patch("backend.api.routes.send_telegram_notification", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = None

        payload = {
            "name": "John Doe",
            "phone": "+1234567890",
            "city": "New York",
            "trade": "Electrician",
            "role": "Contractor",
            "count": 5,
            "notes": "Need ASAP"
        }

        response = client.post("/api/v1/leads/work", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "success", "message": "Lead captured successfully"}

        mock_send.assert_called_once()
        sent_message = mock_send.call_args[0][0]
        assert "John Doe" in sent_message
        assert "tel:+1234567890" in sent_message

def test_create_lead_work_validation_error():
    payload = {
        "name": "John Doe",
        # Missing required fields
    }

    response = client.post("/api/v1/leads/work", json=payload)

    assert response.status_code == 422 # Unprocessable Entity

def test_create_lead_work_telegram_failure():
    with patch("backend.api.routes.send_telegram_notification", new_callable=AsyncMock) as mock_send:
        from fastapi import HTTPException
        mock_send.side_effect = HTTPException(status_code=500, detail="Failed to send notification")

        payload = {
            "name": "Jane Doe",
            "phone": "+0987654321",
            "city": "Los Angeles",
            "trade": "Plumber",
            "role": "Worker",
            "count": 1
        }

        response = client.post("/api/v1/leads/work", json=payload)

        assert response.status_code == 500
        assert response.json() == {"detail": "Failed to send notification"}
