# api/github_test_storage.py

import json
import yaml
import os
from .github_utils import create_file_in_github, get_file_from_github
from api.models import TestCase, TestStep, TestSuite
import datetime


def save_testcase_to_github(testcase, user_id):
    """Save test case and steps to GitHub as a YAML file"""

    test_data = {
        'id': testcase.get('id'),
        'name': testcase['name'],
        'testcase_type':testcase['testcase_type'],
        "testcase_priority":testcase['testcase_priority'],
        'steps': []
    }

    for step in testcase.get('steps', []):
        step_data = {
            'step_number': step.get('step_number'),
            'step_description': step.get('step_description'),
            'step_coordinates': step.get('step_coordinates')
        }
        test_data['steps'].append(step_data)

    # Convert to YAML
    yaml_content = yaml.dump(test_data, default_flow_style=False)

    # Use ID, user_id, project_id in filename
    project_id = testcase['project'].id
    testcase_id = testcase['id']
    file_path = f"testcases/TC_{user_id}_{testcase_id}.yaml"

    # Save to GitHub
    result = create_file_in_github(
        user_id=user_id,
        file_path=file_path,
        content=yaml_content,
        commit_message=f"Create/Update test case: {test_data['name']}"
    )

    result['file_path'] = file_path
    return result

def save_testsuite_to_github(testsuite, user_id):
    suite_data = {
        'id': testsuite['id'],
        'title': testsuite['title'],
        'description': testsuite.get('description', ''),
        'testcase_ids': testsuite.get('testcase', [])
    }

    yaml_content = yaml.dump(suite_data, default_flow_style=False)
    file_path = f"testsuites/TS_{user_id}_{testsuite['id']}.yaml"

    result = create_file_in_github(
        user_id=user_id,
        file_path=file_path,
        content=yaml_content,
        commit_message=f"Create/Update test suite: {suite_data['title']}"
    )
    return result


def get_testcase_from_github(testcase_id, user_id):
    """Get test case from GitHub"""
    file_path = f"testcases/TC_{user_id}_{testcase_id}.yaml"
    result = get_file_from_github(user_id, file_path)
    
    if 'error' in result:
        return None
    
    # Parse YAML content
    try:
        test_data = yaml.safe_load(result['content'])
        return test_data
    except Exception as e:
        return None

def get_testsuite_from_github(testsuite_id, user_id):
    """Get test suite from GitHub"""
    file_path = f"testsuites/TS_{testsuite_id}.yaml"
    result = get_file_from_github(user_id, file_path)
    
    if 'error' in result:
        return None
    
    # Parse YAML content
    try:
        suite_data = yaml.safe_load(result['content'])
        return suite_data
    except Exception as e:
        return None