from django.shortcuts import render

# Create your views here.

import requests
import base64
import json
from django.shortcuts import redirect
from django.http import JsonResponse,HttpRequest
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from api.models import User, GitHubToken
from api.models import *
import os
import time
from automation.views import *


@csrf_exempt
def github_login(request):
    """Redirect user to GitHub OAuth login page"""
    if request.method != "GET":
        return JsonResponse({"error": "Only GET allowed"}, status=405)
    
    user_id = request.GET.get('user_id')
    if not user_id:
        return JsonResponse({"error": "Missing user_id parameter"}, status=400)
        
    # Store user_id in session for retrieval after OAuth
    request.session['github_auth_user_id'] = user_id
    
    github_auth_url = f"https://github.com/login/oauth/authorize?client_id={settings.GITHUB_CLIENT_ID}&scope=repo&redirect_uri={settings.GITHUB_CALLBACK_URL}"
    return redirect(github_auth_url)

@csrf_exempt
def github_callback(request):
    """Handle GitHub OAuth callback"""
    code = request.GET.get('code')
    user_id = request.session.get('github_auth_user_id')
    
    if not code or not user_id:
        return JsonResponse({"error": "Invalid request"}, status=400)
    
    # Exchange code for access token
    token_url = "https://github.com/login/oauth/access_token"
    payload = {
        'client_id': settings.GITHUB_CLIENT_ID,
        'client_secret': settings.GITHUB_CLIENT_SECRET,
        'code': code,
        'redirect_uri': settings.GITHUB_CALLBACK_URL
    }
    headers = {'Accept': 'application/json'}
    
    response = requests.post(token_url, data=payload, headers=headers)
    token_data = response.json()
    
    if 'access_token' not in token_data:
        return JsonResponse({"error": "Failed to get access token"}, status=400)
    
    # Store the token in the database
    try:
        user = User.objects.get(id=user_id)
        github_token, created = GitHubToken.objects.update_or_create(
            user=user,
            defaults={'access_token': token_data['access_token']}
        )
        
        # Redirect to a success page with message
        return redirect('/github')  # Create this page to show success message
        
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

@csrf_exempt
def list_repositories(request):
    """List GitHub repositories for a user"""
    if request.method != "GET":
        return JsonResponse({"error": "Only GET allowed"}, status=405)
    
    user_id = request.GET.get('user_id')
    if not user_id:
        return JsonResponse({"error": "Missing user_id parameter"}, status=400)
    
    try:
        user = User.objects.get(id=user_id)
        github_token = GitHubToken.objects.get(user=user)
    except (User.DoesNotExist, GitHubToken.DoesNotExist):
        return JsonResponse({"error": "GitHub not connected for this user"}, status=404)
    
    # Call GitHub API to list repos
    headers = {
        'Authorization': f'token {github_token.access_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    response = requests.get('https://api.github.com/user/repos', headers=headers)
    
    if response.status_code != 200:
        return JsonResponse({"error": "Failed to fetch repositories"}, status=400)
    
    repos = [{'name': repo['name'], 'full_name': repo['full_name']} for repo in response.json()]
    return JsonResponse({"repositories": repos})

@csrf_exempt
def select_repository(request):
    """Select a repository for storing test cases"""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        repository = data.get('repository')
        
        if not user_id or not repository:
            return JsonResponse({"error": "Missing user_id or repository"}, status=400)
        
        user = User.objects.get(id=user_id)
        github_token = GitHubToken.objects.get(user=user)
        github_token.repository = repository
        github_token.save()
        
        return JsonResponse({"status": "success", "message": "Repository selected successfully"})
        
    except (User.DoesNotExist, GitHubToken.DoesNotExist):
        return JsonResponse({"error": "GitHub not connected for this user"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    

    # api/views.py (Modify existing views)

from .github_test_storage import (
    save_testcase_to_github, 
    save_testsuite_to_github, 
    get_testcase_from_github, 
    get_testsuite_from_github
)
from api.models import GitHubToken

@csrf_exempt
def create_project(request):
    """Create a new project folder and store metadata as JSON"""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        project_name = data.get("project_name")
        project_type = data.get("project_type")
        description = data.get("description")

        if not all([user_id, project_name, project_type, description]):
            return JsonResponse({"error": "All fields are required"}, status=400)

        user = User.objects.get(id=user_id)
        github_token = GitHubToken.objects.get(user=user)

        if not github_token.clone_path:
            return JsonResponse({"error": "Repository not cloned"}, status=400)

        project_path = os.path.join(github_token.clone_path, project_name)

        if os.path.exists(project_path):
            return JsonResponse({"error": f"Project '{project_name}' already exists"}, status=400)

        # Create the project folder
        os.makedirs(project_path)

        # Save metadata as a JSON file
        metadata = {
            "project_name": project_name,
            "project_type": project_type,
            "description": description
        }

        metadata_path = os.path.join(project_path, "project_info.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)

        return JsonResponse({
            "status": "success",
            "message": f"Project '{project_name}' created with metadata",
            "project_path": project_path
        })

    except (User.DoesNotExist, GitHubToken.DoesNotExist):
        return JsonResponse({"error": "GitHub not connected for this user"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def create_testcase(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        project_id = data.get("project_id")

        # GitHub integration check
        try:
            user = User.objects.get(id=user_id)
            github_token = GitHubToken.objects.get(user=user)
        except (User.DoesNotExist, GitHubToken.DoesNotExist):
            return JsonResponse({"error": "GitHub integration missing"}, status=400)

        if not project_id:
            return JsonResponse({"error": "Project ID is required"}, status=400)
        
        if not github_token.clone_path:
            return JsonResponse({"error":"Clone Path is Pending"}, status=400)
        

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return JsonResponse({"error": "Project not found"}, status=404)

        # Generate unique ID for test case
        generated_id = str(uuid.uuid4())[:8]

        testcase_data = {
            "id": generated_id,
            "name": data.get("name"),
            "project": project,
            "testcase_type": data.get("testcase_type", "Functional"),
            "testcase_priority": data.get("testcase_priority", "Medium"),
            "steps": data.get("steps", [])
        }

        # Save to GitHub
        github_result = save_testcase_to_github(testcase_data, user_id)

        if 'error' in github_result:
            return JsonResponse({"error": github_result['error']}, status=500)

        return JsonResponse({
            "status": "success",
            "testcase_id": generated_id,
            "github_storage": True,
            "file_path": github_result.get("file_path")
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

@csrf_exempt
def get_testcase(request, testcase_id, user_id):
    if request.method != "GET":
        return JsonResponse({"error": "Only GET allowed"}, status=405)

    try:
        # Validate GitHub token exists for user
        try:
            user = User.objects.get(id=user_id)
            github_token = GitHubToken.objects.get(user=user)
        except (User.DoesNotExist, GitHubToken.DoesNotExist):
            return JsonResponse({"error": "GitHub token not found for user"}, status=404)

        # Fetch the test case from GitHub
        case_data = get_testcase_from_github(testcase_id, user_id)
        if not case_data:
            return JsonResponse({"error": "TestCase not found in GitHub"}, status=404)

        return JsonResponse(case_data, safe=False)

    except Exception as e:
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

@csrf_exempt
def run_testcase(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests are allowed."}, status=405)

    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        testcase_id = data.get("testcase_id")

        if not user_id or not testcase_id:
            return JsonResponse({"error": "Missing user_id or testcase_id"}, status=400)

        # Step 1: Load test case from GitHub
        testcase = get_testcase_from_github(testcase_id, user_id)

        if not testcase:
            return JsonResponse({"error": "Failed to load test case from GitHub"}, status=404)

        results = []
        steps = testcase.get("steps", [])

        for i, step in enumerate(steps):
            click_x = step.get("step_coordinates", {}).get("click_x", 0)
            click_y = step.get("step_coordinates", {}).get("click_y", 0)
            command = step.get("step_description", "")
            is_final = (i == len(steps) - 1)

            result = Execute_command_internal(
                command=command,
                user_id=user_id,
                click_x=click_x,
                click_y=click_y,
                is_final_step=is_final
            )

            results.append({
                "step_number": i + 1,
                "command": command,
                "response": result
            })

        return JsonResponse({
            "status": "success",
            "testcase_id": testcase_id,
            "executed_steps": results
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    

@csrf_exempt
def create_testsuite(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        user_id = data.get("user_id")
        title = data.get("title")
        description = data.get("description", "")
        testcase_ids = data.get("testcase_ids", [])

        if not user_id or not title or not testcase_ids:
            return JsonResponse({"error": "Missing user_id, title or testcase_ids"}, status=400)

        # Check GitHub integration
        try:
            user = User.objects.get(id=user_id)
            github_token = GitHubToken.objects.get(user=user)
        except (User.DoesNotExist, GitHubToken.DoesNotExist):
            return JsonResponse({"error": "GitHub integration missing"}, status=400)

        # Generate unique suite ID
        generated_id = str(uuid.uuid4())[:8]

        testsuite_data = {
            "id": generated_id,
            "title": title,
            "description": description,
            "testcase": testcase_ids
        }

        github_result = save_testsuite_to_github(testsuite_data, user_id)

        if 'error' in github_result:
            return JsonResponse({"error": github_result['error']}, status=500)

        return JsonResponse({
            "status": "success",
            "testsuite_id": generated_id,
            "github_storage": True,
            "file_path": f"testsuites/TS_{generated_id}.yaml"
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

@csrf_exempt
def get_available_paths(request):
    """Return common system paths for the user to select"""
    if request.method != "GET":
        return JsonResponse({"error": "Only GET allowed"}, status=405)

    # Get standard paths that exist on the system
    paths = []

    # Common directories to check
    standard_paths = [
        {"name": "Home Directory", "path": os.path.expanduser("~")},
        {"name": "Documents", "path": os.path.expanduser("~/Documents")},
        {"name": "Desktop", "path": os.path.expanduser("~/Desktop")},
        {"name": "Downloads", "path": os.path.expanduser("~/Downloads")}
    ]

    # Only include paths that exist and are writable
    for path_info in standard_paths:
        if os.path.exists(path_info["path"]) and os.access(path_info["path"], os.W_OK):
            paths.append(path_info)

    return JsonResponse({"paths": paths})


@csrf_exempt
def clone_repository_to_path(request):
    """Clone the selected repository to the specified path or reuse existing one."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        import subprocess
        data = json.loads(request.body)
        user_id = data.get('user_id')
        selected_path = data.get('selected_path')

        if not user_id or not selected_path:
            return JsonResponse({"error": "Missing user_id or selected_path"}, status=400)

        # Validate selected path exists and is writable
        if not os.path.exists(selected_path) or not os.access(selected_path, os.W_OK):
            return JsonResponse({"error": "Selected path is not valid or not writable"}, status=400)

        # Get user and GitHub token
        user = User.objects.get(id=user_id)
        github_token = GitHubToken.objects.get(user=user)

        if not github_token.repository:
            return JsonResponse({"error": "Please select a repository first"}, status=400)

        repo_name = github_token.repository.split("/")[-1]
        new_clone_path = os.path.join(selected_path, repo_name)

        # ✅ STEP 1: Check if this repo was already cloned
        if github_token.clone_path and os.path.exists(github_token.clone_path):
            return JsonResponse({
                "status": "exists",
                "message": f"Repository already cloned at {github_token.clone_path}",
                "repo_path": github_token.clone_path
            })

        # ✅ STEP 2: Clean up stale path in DB if it was deleted from disk
        if github_token.clone_path and not os.path.exists(github_token.clone_path):
            github_token.clone_path = None
            github_token.save()

        # ✅ STEP 3: Check if new path already exists
        if os.path.exists(new_clone_path):
            return JsonResponse({
                "error": f"Directory {new_clone_path} already exists. Cannot clone here."
            }, status=400)

        # ✅ STEP 4: Clone the repository
        clone_url = f"https://{github_token.access_token}@github.com/{github_token.repository}.git"
        result = subprocess.run(
            ["git", "clone", clone_url, new_clone_path],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return JsonResponse({"error": f"Git clone failed: {result.stderr}"}, status=400)

        # ✅ STEP 5: Save new clone path
        github_token.clone_path = new_clone_path
        github_token.save()

        # Store in session (optional)
        request.session['local_repo_path'] = new_clone_path

        return JsonResponse({
            "status": "success",
            "message": "Repository cloned successfully",
            "repo_path": new_clone_path
        })

    except (User.DoesNotExist, GitHubToken.DoesNotExist):
        return JsonResponse({"error": "GitHub not connected for this user"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def run_testsuite(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        suite_id = data.get("testsuite_id")
        user_id = data.get("user_id")
        wait_between_steps = data.get("wait_between_steps", 1000)  # in ms
        wait_between_cases = data.get("wait_between_cases", 3000)  # in ms

        if not suite_id or not user_id:
            return JsonResponse({"error": "Missing testsuite_id or user_id"}, status=400)

        # Check GitHub token availability
        try:
            user = User.objects.get(id=user_id)
            github_token = GitHubToken.objects.get(user=user)
        except (User.DoesNotExist, GitHubToken.DoesNotExist):
            return JsonResponse({"error": "GitHub token not found for user"}, status=404)

        # Fetch test suite from GitHub
        suite_data = get_testsuite_from_github(suite_id, user_id)
        if not suite_data:
            return JsonResponse({"error": "TestSuite not found in GitHub"}, status=404)

        testcase_ids = suite_data['testcase_ids']
        suite_title = suite_data['title']

        results = {
            "testsuite_id": suite_id,
            "testsuite_title": suite_title,
            "user_id": user_id,
            "testcases": []
        }

        for case_index, case_id in enumerate(testcase_ids):
            if case_index > 0:
                time.sleep(wait_between_cases / 1000)

            # Fetch each test case from GitHub
            case_data = get_testcase_from_github(case_id, user_id)
            if not case_data:
                results["testcases"].append({
                    "testcase_id": case_id,
                    "status": "TestCase not found in GitHub"
                })
                continue

            case_name = case_data['name']
            steps = case_data.get('steps', [])

            case_result = {
                "testcase_id": case_id,
                "testcase_name": case_name,
                "steps": []
            }

            total_cases = len(testcase_ids)
            total_steps = len(steps)

            for step_index, step in enumerate(steps):
                if step_index > 0:
                    time.sleep(wait_between_steps / 1000)

                command = step.get('step_description')
                click_x = step.get('step_coordinates', {}).get('click_x')
                click_y = step.get('step_coordinates', {}).get('click_y')
                is_final_step = (case_index == total_cases - 1) and (step_index == total_steps - 1)

                try:
                    response = Execute_command_internal(command, user_id, click_x, click_y, is_final_step=is_final_step)
                    is_successful = (
                        response.get('status') == 'success' or
                        'browser opened' in str(response.get('status', '')) or
                        'Click performed' in str(response.get('status', '')) or
                        'Type performed' in str(response.get('status', '')) or
                        'Verify performed' in str(response.get('status', '')) or
                        'Get performed' in str(response.get('status', ''))
                    )
                    step_result = 'passed' if is_successful else 'failed'
                    case_result["steps"].append({
                        "step_number": step['step_number'],
                        "command": command,
                        "result": step_result,
                        "response": response
                    })

                except Exception as e:
                    case_result["steps"].append({
                        "step_number": step['step_number'],
                        "command": command,
                        "result": "failed",
                        "error": str(e)
                    })

            passed_steps = sum(1 for s in case_result["steps"] if s["result"] == "passed")
            total_step_count = len(case_result["steps"])
            case_result["summary"] = {
                "total_steps": total_step_count,
                "passed_steps": passed_steps,
                "status": "passed" if passed_steps == total_step_count else "failed"
            }

            results["testcases"].append(case_result)

        total_cases = len(results["testcases"])
        passed_cases = sum(1 for case in results["testcases"] if case.get("summary", {}).get("status") == "passed")
        results["summary"] = {
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "status": "passed" if passed_cases == total_cases else "failed"
        }

        return JsonResponse(results)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)


def Execute_command_internal(command, user_id, click_x, click_y, is_final_step):
    request_data = {
        "command": command,
        "user_id": user_id,
        "click_x": click_x,
        "click_y": click_y,
        "is_final_step": is_final_step
    }

    fake_request = HttpRequest()
    fake_request.method = "POST"
    fake_request._body = json.dumps(request_data).encode("utf-8")

    return json.loads(Execute_command(fake_request).content.decode())
