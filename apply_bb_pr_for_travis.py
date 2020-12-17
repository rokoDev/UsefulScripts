#!/usr/bin/env python3

import requests
import os
import subprocess
import argparse

def run(*args):
  try:
    return subprocess.run(['git'] + list(args), capture_output=True, text=True).stdout
  except subprocess.CalledProcessError:
    return None

def get_current_branch_name():
  return run("rev-parse", "--abbrev-ref", "HEAD").rstrip('\r\n')

def submodule_update_init_recursive():
  return run("submodule", "update", "--init", "--recursive")

def switch_to_branch(branch_name):
  CURRENT_BRANCH = get_current_branch_name()
  if CURRENT_BRANCH == branch_name:
    print(f"we are already on source branch <{branch_name}>")
  else:
    print(f"switch branch from <{CURRENT_BRANCH}> to <{branch_name}>")
    run("checkout", "--recurse-submodules", branch_name)
    submodule_update_init_recursive()

def create_and_checkout_branch(branch_name):
  print(f"create and checkout branch <{branch_name}>")
  run("checkout", "-b", branch_name)

def merge_branch_to_current(branch_name):
  CURRENT_BRANCH = get_current_branch_name()
  print(f"merge <{branch_name}> to <{CURRENT_BRANCH}>")
  run("merge", branch_name)

def get_source_and_target_branch_names(session, slug, pr_number):
  response = session.get(f"https://bitbucket.org/api/2.0/repositories/{slug}/pullrequests/{pr_number}")
  if response.status_code == 200:
    data = response.json()
    PR_SOURCE_BRANCH = data['source']['branch']['name']
    PR_DESTINATION_BRANCH = data['destination']['branch']['name']
    return PR_SOURCE_BRANCH, PR_DESTINATION_BRANCH
  else:
    error_code = response.status_code
    sys.exit(f"Fail to retrive pull request info: {error_code}")
    return "", ""

def main():
  parser = argparse.ArgumentParser(description="""
  This script does:
    1. Figure out source and destination branch names.
    2. Create new branch from destination branch.
    3. Merge source branch to destination branch.
  """)
  parser.add_argument("--BB_LOGIN", default=os.getenv('BB_LOGIN'), help="Bitbucket login.")
  parser.add_argument("--BB_PASSWORD", default=os.getenv('BB_PASSWORD'), help="Bitbucket password.")
  parser.add_argument("--PR_NUMBER", default=os.getenv('TRAVIS_PULL_REQUEST'), help="Pull request number.")
  parser.add_argument("--PR_SLUG", default=os.getenv('TRAVIS_PULL_REQUEST_SLUG'), help="repo_owner_name/repo_name.")
  parser.add_argument("--PROJECT_ROOT_PATH", default=os.getenv('TRAVIS_BUILD_DIR'), help="Path to project directory containing hidden .git directory.")

  args = parser.parse_args()

  BB_LOGIN = args.BB_LOGIN
  BB_PASSWORD = args.BB_PASSWORD
  PR_NUMBER = args.PR_NUMBER
  PR_SLUG = args.PR_SLUG
  PROJECT_ROOT_PATH = args.PROJECT_ROOT_PATH
  
  # set credentials
  s = requests.Session()
  s.auth = (BB_LOGIN, BB_PASSWORD)
  
  # get source and destination branch names
  PR_SOURCE_BRANCH, PR_DESTINATION_BRANCH = get_source_and_target_branch_names(s, PR_SLUG, PR_NUMBER)
  
  os.chdir(PROJECT_ROOT_PATH)
  switch_to_branch(PR_SOURCE_BRANCH)

  switch_to_branch(PR_DESTINATION_BRANCH)

  PR_BRANCH_NAME = f"pr-{PR_NUMBER}"
  create_and_checkout_branch(PR_BRANCH_NAME)

  merge_branch_to_current(PR_SOURCE_BRANCH)

  submodule_update_init_recursive()

if __name__ == "__main__":
  main()
