# api/github_utils.py

import requests
import base64
import json
import os
import time
from django.conf import settings
from api.models import User, GitHubToken, TestCase, TestStep, TestSuite

def get_github_token(user_id):
    """Get GitHub token for a user"""
    try:
        user = User.objects.get(id=user_id)
        github_token = GitHubToken.objects.get(user=user)
        return github_token
    except (User.DoesNotExist, GitHubToken.DoesNotExist):
        return None

def create_file_in_github(user_id, file_path, content, commit_message="Update test case"):
    """Create or update a file in GitHub repository"""
    github_token = get_github_token(user_id)
    if not github_token or not github_token.repository:
        return {"error": "GitHub not connected or repository not selected"}

    headers = {
        'Authorization': f'token {github_token.access_token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    repo_url = f"https://api.github.com/repos/{github_token.repository}/contents/{file_path}"
    response = requests.get(repo_url, headers=headers)

    content_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')

    # If file exists, update it
    if response.status_code == 200:
        file_sha = response.json()['sha']
        payload = {
            'message': commit_message,
            'content': content_encoded,
            'sha': file_sha
        }
        update_resp = requests.put(repo_url, headers=headers, json=payload)
        if update_resp.status_code in [200, 201]:
            return {"status": "success", "message": "File updated successfully"}
        else:
            return {"error": f"Failed to update file: {update_resp.json().get('message', 'Unknown error')}"}

    # If file doesn't exist, create it
    elif response.status_code == 404:
        payload = {
            'message': commit_message,
            'content': content_encoded
        }
        create_resp = requests.put(repo_url, headers=headers, json=payload)
        if create_resp.status_code in [200, 201]:
            return {"status": "success", "message": "File created successfully"}
        else:
            return {"error": f"Failed to create file: {create_resp.json().get('message', 'Unknown error')}"}

    else:
        return {"error": f"Failed to check file existence: {response.json().get('message', 'Unknown error')}"}
    
def get_file_from_github(user_id, file_path):
    """Get file content from GitHub repository"""
    github_token = get_github_token(user_id)
    if not github_token or not github_token.repository:
        return {"error": "GitHub not connected or repository not selected"}
    
    headers = {
        'Authorization': f'token {github_token.access_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    repo_url = f"https://api.github.com/repos/{github_token.repository}/contents/{file_path}"
    response = requests.get(repo_url, headers=headers)
    
    if response.status_code == 200:
        content_encoded = response.json()['content']
        content = base64.b64decode(content_encoded).decode('utf-8')
        return {"status": "success", "content": content}
    else:
        return {"error": f"Failed to get file: {response.json().get('message', 'File not found')}"}