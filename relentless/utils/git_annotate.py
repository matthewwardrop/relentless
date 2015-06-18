import git
import subprocess
import os
from .xelatex import XeLaTeX

def get_commits_by_branch(repo='.',branches=None):

    commits = {}
    all_commits = []

    r = git.Repo(repo)

    if branches is None:
        branches = [b.name for b in r.branches]
        branches.remove('master')
        branches.insert(0,'master')

    for branch in branches:
        cs = []
        for c in r.iter_commits(rev=branch):
            cs.append(c)
            if c not in all_commits:
                all_commits.append(c)
        commits[branch] = cs


    all_commits = sorted(all_commits, key=lambda commit: commit.committed_date, reverse=False)

    return branches, commits, all_commits

class GitAnnotate(XeLaTeX):

    def template(self):
        with open(os.path.join(os.path.dirname(__file__),'templates','git_annotate.tex')) as f:
            return f.read()

    def process(self, output='history', repo='.', annotate={}, branches=None):

        branches, commits, all_commits = get_commits_by_branch(repo, branches)

        output = {}

        output['branchcount'] = len(branches)
        output['commitcount'] = len(all_commits)

        output['branches'] = []
        for i, branch in enumerate(branches):
            output['branches'].append( r"\branch{%d}{%s}" % (i, branch) )
        output['branches'] = '\n'.join(output['branches'])

        output['commits'] = []
        for d,commit in enumerate(all_commits):
            for branch in branches:
                if commit in commits[branch]:
                    break
            i = branches.index(branch)
            rel, value = annotate.get(commit.hexsha,(0,""))

            output['branches'].append( r"\commit{%d}{%d}{%s}{%s}{%f}{%s}" % (i, d, commit.hexsha[:7], commit.message, rel, value) )
        output['commits'] = '\n'.join(output['commits'])

        output['connects'] = []
        for d,commit in enumerate(all_commits):
            for parent in commit.parents:
                output['connects'].append( r"\connect{%s}{%s};" % (parent.hexsha[:7], commit.hexsha[:7]) )
        output['connects'] = '\n'.join(output['connects'])

        return output
