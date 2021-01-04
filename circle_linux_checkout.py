#!/usr/bin/env python3

import requests
import os
import subprocess
import argparse
import sys
from circle_linux_configure_build_test import cmake_configure_build_test

def run(*args):
  command = ['git'] + list(args)
  separator = ' '
  print(f"Current command: [{separator.join(command)}]")
  try:
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    return result.stdout
  except subprocess.CalledProcessError as e:
    s = " "
    print(f"Command [{s.join(command)}] exit with code {e.returncode}")
    print(f"Command output: {e.output}")
    print(f"Command stderr: {e.stderr}")
    sys.exit(e.returncode)

def get_current_branch_name():
  return run("rev-parse", "--abbrev-ref", "HEAD").rstrip('\r\n')

def submodule_update_init_recursive():
  return run("submodule", "update", "--init", "--recursive")

# we assume that every submodule tracking "master" branch.
# If that is not true additional workaround needed to determine submodule branch name.
def checkout_all_submodules():
  run("submodule", "foreach", "--recursive", "git", "checkout", "master")

def update_all_submodules():
  checkout_all_submodules()
  submodule_update_init_recursive()

def switch_to_branch(branch_name):
  CURRENT_BRANCH = get_current_branch_name()
  if CURRENT_BRANCH == branch_name:
    print(f"we are already on source branch <{branch_name}>")
  else:
    print(f"switch branch from <{CURRENT_BRANCH}> to <{branch_name}>")
    run("checkout", "--recurse-submodules", branch_name)
    update_all_submodules()

def create_and_checkout_branch(branch_name):
  print(f"create and checkout branch <{branch_name}>")
  run("checkout", "-b", branch_name)

def merge_branch_to_current(branch_name):
  CURRENT_BRANCH = get_current_branch_name()
  print(f"merge <{branch_name}> to <{CURRENT_BRANCH}>")
  run("merge", branch_name)

def checkout_pr(pr_number):
  pr_branch_name = f"pr{pr_number}"
  print(f"checkout_pr to branch:<{pr_branch_name}>")
  run("fetch", "origin", f"pull/{pr_number}/head:{pr_branch_name}")
  return pr_branch_name

def clone_branch(clone_url, branch_name):
  run("clone", "-b", branch_name, "--single-branch", clone_url)

def clone_repo(clone_url):
  run("clone", clone_url)

def main():
  parser = argparse.ArgumentParser(description="""
  This script does:
    1. Figure out source and destination branch names.
    2. Create new branch from destination branch.
    3. Merge source branch to destination branch.
  """)
  parser.add_argument("-CLONE_URL", default=os.environ['CIRCLE_REPOSITORY_URL'], help="URL which can be used in command:$ git clone URL")
  parser.add_argument("-OWNER_NAME", default=os.environ['CIRCLE_PROJECT_USERNAME'], help="Repository owner name.")
  parser.add_argument("-REPO_NAME", default=os.environ['CIRCLE_PROJECT_REPONAME'], help="Repository name.")
  parser.add_argument("-PR_URL", default=os.environ['CIRCLE_PULL_REQUEST'], help="Pull request url.")
  parser.add_argument("-CI_WORK_PATH", default=os.environ['CIRCLE_WORKING_DIRECTORY'], help="CI working directory.")
  parser.add_argument("-BRANCH", default=os.environ['CIRCLE_BRANCH'], help="CI working directory.")

  args = parser.parse_args()

  CLONE_URL = args.CLONE_URL
  REPO_NAME = args.REPO_NAME
  OWNER_NAME = args.OWNER_NAME
  PR_NUMBER = os.path.basename(args.PR_URL)
  CI_WORK_PATH = args.CI_WORK_PATH
  BRANCH = args.BRANCH

  print(f"CLONE_URL:<{CLONE_URL}>")
  print(f"OWNER_NAME:<{OWNER_NAME}>")
  print(f"REPO_NAME:<{REPO_NAME}>")
  print(f"CI_WORK_PATH:<{CI_WORK_PATH}>")

  path = None
  if PR_NUMBER.isdigit():
    path = os.path.join(CI_WORK_PATH, OWNER_NAME, REPO_NAME, f"pr{PR_NUMBER}")
  else:
    path = os.path.join(CI_WORK_PATH, OWNER_NAME, REPO_NAME, BRANCH)
  print(f"path:<{path}>")
  os.makedirs(path, exist_ok=True)

  os.chdir(path)
  PROJECT_ROOT_PATH = os.path.join(path, REPO_NAME)
  if not os.path.isdir(PROJECT_ROOT_PATH):
    if PR_NUMBER.isdigit():
      clone_repo(CLONE_URL)
      os.chdir(PROJECT_ROOT_PATH)
      #switch_to_branch("master")
      pr_branch_name = checkout_pr(PR_NUMBER)
      switch_to_branch(pr_branch_name)
    else:
      clone_branch(CLONE_URL, BRANCH)
      os.chdir(PROJECT_ROOT_PATH)
      switch_to_branch(BRANCH)

  NOT_CLEAR_BUILD_DIR = False

  BUILD_DIR = os.path.join(PROJECT_ROOT_PATH, 'build', 'Ninja', 'Debug')
  cmake_configure_build_test(False, NOT_CLEAR_BUILD_DIR, 'Debug', 'Ninja', BUILD_DIR, PROJECT_ROOT_PATH)

  BUILD_DIR = os.path.join(PROJECT_ROOT_PATH, 'build', 'Ninja', 'Release')
  cmake_configure_build_test(False, NOT_CLEAR_BUILD_DIR, 'Release', 'Ninja', BUILD_DIR, PROJECT_ROOT_PATH)

if __name__ == "__main__":
  main()