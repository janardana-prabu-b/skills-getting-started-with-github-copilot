"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


class TestActivitiesEndpoint:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_200(self, client):
        """Test that GET /activities returns status 200"""
        response = client.get("/activities")
        assert response.status_code == 200

    def test_get_activities_returns_dict(self, client):
        """Test that GET /activities returns a dictionary"""
        response = client.get("/activities")
        data = response.json()
        assert isinstance(data, dict)

    def test_get_activities_contains_chess_club(self, client):
        """Test that activities include Chess Club"""
        response = client.get("/activities")
        data = response.json()
        assert "Chess Club" in data

    def test_activity_has_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)

    def test_participants_are_strings(self, client):
        """Test that all participants are email strings"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            for participant in activity_details["participants"]:
                assert isinstance(participant, str)
                assert "@" in participant  # Basic email validation


class TestSignupEndpoint:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_for_activity_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Programming%20Class/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]

    def test_signup_adds_participant_to_list(self, client):
        """Test that signup actually adds the participant"""
        email = "test@mergington.edu"
        activity = "Art Studio"
        
        # First signup
        response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert response.status_code == 200
        
        # Check activities to verify participant was added
        activities = client.get("/activities").json()
        assert email in activities[activity]["participants"]

    def test_signup_duplicate_email_fails(self, client):
        """Test that signing up with duplicate email returns error"""
        email = "michael@mergington.edu"
        activity = "Chess Club"
        
        response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"].lower()

    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signing up for nonexistent activity returns 404"""
        response = client.post(
            "/activities/NonExistent/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_signup_with_url_encoded_activity_name(self, client):
        """Test signup with URL-encoded activity names"""
        response = client.post(
            "/activities/Basketball%20Team/signup?email=newplayer@mergington.edu"
        )
        assert response.status_code == 200


class TestUnregisterEndpoint:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_success(self, client):
        """Test successful unregister from an activity"""
        email = "michael@mergington.edu"
        activity = "Chess Club"
        
        response = client.delete(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Unregistered" in data["message"]

    def test_unregister_removes_participant(self, client):
        """Test that unregister actually removes the participant"""
        email = "john@mergington.edu"
        activity = "Gym Class"
        
        # Verify participant exists before unregister
        activities = client.get("/activities").json()
        assert email in activities[activity]["participants"]
        
        # Unregister
        response = client.delete(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert response.status_code == 200
        
        # Verify participant is removed
        activities = client.get("/activities").json()
        assert email not in activities[activity]["participants"]

    def test_unregister_nonexistent_participant_fails(self, client):
        """Test that unregistering a non-participant returns error"""
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=nobody@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"].lower()

    def test_unregister_nonexistent_activity_fails(self, client):
        """Test that unregistering from nonexistent activity returns 404"""
        response = client.delete(
            "/activities/NonExistent/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


class TestRootEndpoint:
    """Tests for GET / endpoint"""

    def test_root_redirects_to_static_index(self, client):
        """Test that root endpoint redirects to /static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestIntegration:
    """Integration tests for multi-step workflows"""

    def test_signup_and_unregister_workflow(self, client):
        """Test complete workflow of signing up and then unregistering"""
        email = "integration@mergington.edu"
        activity = "Tennis Club"
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify in list
        activities = client.get("/activities").json()
        assert email in activities[activity]["participants"]
        initial_count = len(activities[activity]["participants"])
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify removed from list
        activities = client.get("/activities").json()
        assert email not in activities[activity]["participants"]
        assert len(activities[activity]["participants"]) == initial_count - 1

    def test_multiple_signups_same_activity(self, client):
        """Test that multiple different users can sign up for the same activity"""
        activity = "Science Club"
        emails = ["student1@mergington.edu", "student2@mergington.edu"]
        
        for email in emails:
            response = client.post(
                f"/activities/{activity}/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify both are in the list
        activities = client.get("/activities").json()
        for email in emails:
            assert email in activities[activity]["participants"]
