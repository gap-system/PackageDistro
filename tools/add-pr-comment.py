#!/usr/bin/env python3

import json
import os
import sys

from github import Github

def read_json(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def add_or_update_pr_comment():
    # search the pull request that triggered this action
    gh = Github(os.getenv('GITHUB_TOKEN'))
    event = read_json(os.getenv('GITHUB_EVENT_PATH'))
    repo = gh.get_repo(event['repository']['full_name'])
    pr = repo.get_pull(event['number'])

    # check if this pull request has a duplicated comment
    for c in pr.get_issue_comments():
        print("comment by user {} with body {}".format(c.user.login, c.body))
        #if c.user.login == 'TODO' && c.body MATCHES:
        #    TODO UPDATE
        #    c.edit("TODO")
        #    return
    
    # add a new the comment
    print("creating PR comment")
    pr.create_issue_comment("This is a comment")


if __name__ == "__main__":
    add_or_update_pr_comment()

