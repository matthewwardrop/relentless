import git
import subprocess
import os

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



def annotate(output='history', repo='.', annotate={}, branches=None, cwd=None):
    f = open(output+'.tex','w')

    header = r"""
    \documentclass{standalone}
    \usepackage{tikz}
    \usepackage{fancyvrb}
    \usetikzlibrary{calc}
    \usetikzlibrary{positioning}
    \usepackage{filecontents}

    \pgfmathsetmacro{\xscaling}{1.2}
    \pgfmathsetmacro{\yscaling}{2}
    \pgfmathsetmacro{\perfwidth}{3 em}
    \pgfmathsetmacro{\branchcount}{%d}
    \pgfmathsetmacro{\branchcountd}{\branchcount+1}
    \pgfmathsetmacro{\branchcountm}{\branchcount-1}
    \pgfmathsetmacro{\count}{%d}
    \pgfmathsetmacro{\countm}{\count-1}
    \pgfmathsetmacro{\perfbarwidth}{0.8 em}

    \newcommand\branch[2]{
        \node[branch] (#2) at (\xscaling * #1 em, \yscaling * \count em ) {#2};
        \node[branch,anchor=east] (#2) at (\xscaling * #1 em, -1*\yscaling em ) {#2};
        }
    \newcommand\commit[6]{
        \node[commit] (#3) at (\xscaling * #1 em, \yscaling * #2 em) {};
        \draw[solid, thick, black, line width=\perfbarwidth] (-\xscaling em, \yscaling * #2 em) -- (-\xscaling em - #5*\perfwidth, \yscaling * #2 em);
        \node[anchor=east] at (-\xscaling em - \perfwidth -\xscaling, \yscaling * #2 em) {#6};
        \node[clabel] at ($(#3 -| \xscaling*\branchcount em, 0)$) {\Verb!#3: #4!};
        }
    \newcommand\ghost[1]{\coordinate (#1);}
    \newcommand\connect[2]{\path (#1) to[out=90,in=-90] (#2);}

    \begin{document}
    \begin{tikzpicture}
    \tikzstyle{branch}=[rotate=90,anchor=west]
    \tikzstyle{commit}=[draw,circle,fill=white,inner sep=0pt,minimum size=5pt]
    \tikzstyle{perf}=[draw,circle,fill=black,inner sep=0pt,minimum size=3pt]
    \tikzstyle{clabel}=[right,outer sep=1em]
    \tikzstyle{every path}=[draw]

    \foreach \x in {0,...,\branchcountm}{
        \draw[dashed] (\xscaling*\x em,-1*\yscaling em) -- (\xscaling*\x em,\yscaling*\count em);
    }
    \draw[solid] (-\xscaling em,-1*\yscaling em) -- (-\xscaling em,\yscaling*\count em);
    \draw[solid] (-\xscaling em - \perfwidth,-1*\yscaling em) -- (-\xscaling em - \perfwidth,\yscaling*\count em);

    \foreach \y in {0,...,\countm}{
        \draw[dashed] (-\xscaling em,\yscaling*\y em) -- (\xscaling*\branchcountd em,\yscaling*\y em);
    }

    """

    middle = r"""
    """

    footer = r"""
    \end{tikzpicture}
    \end{document}
    """

    branches, commits, all_commits = get_commits_by_branch(repo, branches)

    def prepare(string):
        return string.replace('^','\^').replace('_','').replace("'","").replace('"',"").strip()

    f.write( header% (len(branches),len(all_commits)) )

    for i, branch in enumerate(branches):
        f.write( r"\branch{%d}{%s}" % (i, prepare(branch)) + "\n" )

    for d,commit in enumerate(all_commits):
        for branch in branches:
            if commit in commits[branch]:
                break
        #       branch = commit.name_rev.split()[1].split('~')[0]
        i = branches.index(branch)
        rel, value = annotate.get(commit.hexsha,(0,""))

        f.write( r"\commit{%d}{%d}{%s}{%s}{%f}{%s}\\" % (i, d, commit.hexsha[:7], prepare(commit.message) + "\n", rel, value) )

    f.write( middle )

    for d,commit in enumerate(all_commits):
        for parent in commit.parents:
            f.write( r"\connect{%s}{%s};" % (parent.hexsha[:7], commit.hexsha[:7]) + "\n" )

    f.write( footer )

    f.close()

    if cwd is None:
        cwd = os.path.dirname(output)
    subprocess.Popen(['xelatex',output], cwd=cwd).wait()
