#!/usr/bin/env python3

import requests
import os
import subprocess
import argparse

def run(*args):
    return subprocess.check_call(['git'] + list(args))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""
    This script does:
      1. Figure out source and destination branch names. Set env vars: PR_SOURCE_BRANCH and PR_DESTINATION_BRANCH.
      2. Download pull request from https://bitbucket.org to a file. Path to file saved in PR_PATCH_PATH environment variable.
      3. Create new branch from destination branch. New branch name can be taken form PR_BRANCH_NAME environment variable.
      4. Apply patch and do commit.
    """)
    parser.add_argument("--BB_LOGIN", default=os.getenv('BB_LOGIN') help="Bitbucket login.")
    parser.add_argument("--BB_PASSWORD", default=os.getenv('BB_PASSWORD'), help="Bitbucket password.")
    parser.add_argument("--PR_NUMBER", default=os.getenv('TRAVIS_PULL_REQUEST'), help="Pull request number.")
    parser.add_argument("--PR_SLUG", default=os.getenv('TRAVIS_PULL_REQUEST_SLUG'), help="repo_owner_name/repo_name.")
    parser.add_argument("--PROJECT_ROOT_PATH", default=os.getenv('TRAVIS_BUILD_DIR'), help="Path to project directory containing hidden .git directory.")
    parser.add_argument("--PR_PATCH_PATH", help="Path to directory where patch will be saved. If not set it will be parent of PROJECT_ROOT_PATH")

    args = parser.parse_args()

    BB_LOGIN = args.BB_LOGIN
    BB_PASSWORD = args.BB_PASSWORD
    PR_NUMBER = args.PR_NUMBER
    PR_SLUG = args.PR_SLUG
    PROJECT_ROOT_PATH = args.PROJECT_ROOT_PATH
    PR_PATCH_PATH = args.PR_PATCH_PATH


    PR_PATCH_FILE_NAME = f"pr{PR_NUMBER}.patch"
    if not os.path.exists(os.path.dirname(PR_PATCH_PATH)):
      head, tail = os.path.split(PROJECT_ROOT_PATH)
      PR_PATCH_FULL_PATH = os.path.join(head, PR_PATCH_FILE_NAME)
    else:
      PR_PATCH_FULL_PATH = os.path.join(PR_PATCH_PATH, PR_PATCH_FILE_NAME)
    
    # set credentials
    s = requests.Session()
    s.auth = (BB_LOGIN, BB_PASSWORD)
    
    # get source and destination branch names
    response = s.get(f"https://bitbucket.org/api/2.0/repositories/{PR_SLUG}/pullrequests/{PR_NUMBER}")
    if response.status_code == 200:
      data = response.json()
      os.environ['PR_SOURCE_BRANCH'] = data['source']['branch']['name']
      os.environ['PR_DESTINATION_BRANCH'] = data['destination']['branch']['name']
    else:
      error_code = response.status_code
      sys.exit(f"Fail to retrive pull request info: {error_code}")
    
    # get patch file with pull request data
    response = s.get(f"https://bitbucket.org/api/2.0/repositories/{PR_SLUG}/pullrequests/{PR_NUMBER}/patch")
    if response.status_code == 200:
      with open(PR_PATCH_FULL_PATH, 'wb') as f:
        f.write(response.content)
        os.environ['PR_PATCH_FULL_PATH'] = PR_PATCH_FULL_PATH
        os.environ['PR_PATCH_FILE_NAME'] = PR_PATCH_FILE_NAME
    else:
      error_code = response.status_code
      sys.exit(f"Fail to retrive pull request patch: {error_code}")
    
    
    os.chdir(os.path.dirname(PROJECT_ROOT_PATH))
    run("checkout", os.getenv('PR_DESTINATION_BRANCH'))
    run("checkout", "-b", os.getenv('PR_BRANCH_NAME'), os.getenv('PR_DESTINATION_BRANCH'))
    os.environ['PR_BRANCH_NAME'] = f"pr-{PR_NUMBER}"
    run("apply", os.getenv('PR_PATCH_FULL_PATH'))
    run("commit", "-am", f"pull request {PR_NUMBER}")
