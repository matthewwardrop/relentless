import subprocess

import scipy.optimize as spo

import sys, os, re, time, git, shelve, shutil

import parampy, numpy as np

from .computations import *

from multiprocessing import Lock

class Tester(object):

    computation_types = {
        'simple': SimpleComputation,
        'marathon': MarathonComputation
    }

    def __init__(self, project, computation_type=SimpleComputation, computation_wrapper=None, working_dir='_relentless', cache=True, **kwargs):
        if type(computation_type) is str:
            try:
                computation_type = self.computation_types[computation_type]
            except:
                raise ValueError("Invalid computation type: %s" % computation_type)
        if not issubclass(computation_type, Computation):
            raise ValueError("Invalid computation_type provided.")
        self.computation_type = computation_type
        self.computation_wrapper = computation_wrapper

        self.lock = Lock()

        self.project_dir = os.path.abspath(os.path.dirname(project))
        self.working_dir = working_dir
        if not os.path.exists(self.path("")):
            os.makedirs(self.path(""))

        self.project = os.path.basename(project)

        self.p = parampy.Parameters()

        self.init(**kwargs)

    def path(self, filename):
        return os.path.join(self.project_dir, self.working_dir, filename)

    def init(self):
        pass

    def cache(self, value=None, task=0, params={}):
        if len(params) > 0:
            return value
        s = shelve.open(self.path('tester_cache.cache'))
        try:
            key = self.get_cache_key(task=task, params=params)
            if value is None:
                if key in s.keys():
                    return s[key]
                return None
            else:
                s[key] = value
                return value
        except ValueError:
            return value
        except Exception, e:
            raise e
        finally:
            s.close()

    def get_cache_key(self, task=0, params={}):
        return str(task)

    @property
    def computation(self):
        with self.lock:
            if getattr(self,'_computation',None) is not None:
                return self._computation
            self._computation = self.get_computation()
            return self._computation

    def get_computation(self):
        return self.computation_type(self.project, directory=self.project_dir, wrapper=self.computation_wrapper)

    def cleanup(self):
        self._computation = None
        self._cleanup()

    def _cleanup(self):
        pass

    def run(self,task=0,params={}):
        task = int(task)
        result = self.cache(task=task, params=params)
        if result is None:
            result = self.cache(value=self.computation.run(task,params),task=task,params=params)
        return result

    def score(self, *args, **kwargs):
        return self.run(*args,**kwargs).score

    def __tasks(self,count=1, tasks=None):
        if tasks is None:
            return range(1,count+1)
        return tasks

    def iterate_score(self,*args,**kwargs):
        results = self.iterate(*args,**kwargs)
        def scores(r):
            return r.score
        return np.vectorize(scores)(results).astype(float)

    def iterate(self,count=1,tasks=None,ranges=None,params={},iter_opts={}):
        if ranges is None:
            ranges = []
        def f(params):
            task = int(params.pop('task'))
            return self.run(task=task, params=params)
        if type(ranges) is dict:
            ranges = [ranges]
        ranges.insert(0,{'task':self.__tasks(count, tasks)})
        iterator = self.p.ranges_iterator(ranges, params=params, function=f, **iter_opts)
        results = np.empty(iterator.ranges_eval.shape, dtype=object)
        for index,data in iterator:
            results[index] = data
        return results

    def optimise(self,opt_params=[],count=1,tasks=None,params={},opt_opts={}):
        '''
        This will only work for non-discrete scores.
        '''
        x0 = []
        for opt_param in opt_params:
            if opt_param not in params:
                raise ValueError("Default value must be supplied for %s" % opt_param)
            x0.append(params[opt_param])
        f = self.__iterate_wrapper(opt_params, count, tasks, params)
        r = spo.minimize(f, x0, tol=1e-3, **opt_opts)
        x = {}
        for i,opt_param in enumerate(opt_params):
            x[opt_param] = r.x[i]
        return x, r.success

    def __iterate_wrapper(self,opt_params=[],count=1,tasks=None,params={}):
        params = params.copy()
        def wrapped(x):
            for i,opt_param in enumerate(opt_params):
                params[opt_param] = x[i]
            return self.iterate_score(count=count,tasks=tasks,params=params)
        return wrapped

    def __enter__(self):
        return self

    def __exit__(self,type,value,traceback):
        self.cleanup()

    def __del__(self):
        self.cleanup()

class GitTester(Tester):

    def init(self, ref='master'):
        self.ref = ref

    @property
    def ref(self):
        return self.__ref
    @ref.setter
    def ref(self, ref):
        self.cleanup()
        self.__ref = ref
        self.computation

    def get_repo_dir(self):
        return self.path(self.ref)

    def get_cache_key(self, task=0, params={}):
        ref = str(self.__repo.commit().hexsha)
        return '%s_%s'%(ref,task)

    def get_computation(self):
        d = self.get_repo_dir()
        if os.path.exists(d):
            self.__repo = git.Repo(d)
            self.__repo.remotes.origin.pull()
        else:
            self.__repo = git.Repo(self.project_dir).clone(d)
        self.__repo.git.checkout(self.ref)
        return self.computation_type(self.project, directory=d, wrapper=self.computation_wrapper)

    def _cleanup(self):
        if getattr(self, '_GitTester__ref', None) is not None:
            d = self.get_repo_dir()
            if os.path.exists(d):
                shutil.rmtree(d)

    def annotate_commits(self, count=1, output='history', branches=None, since=None, iter_opts={}):
        from .utils.git_history import annotate, get_commits_by_branch

        annotations = {}
        branches, commits, all_commits = get_commits_by_branch(self.project_dir, branches=branches)

        going = False
        if since is None:
            going = True

        max_score = -1

        for commit in all_commits:
            if not going and commit.hexsha.startswith(since):
                going = True
            if going:
                self.ref = commit.hexsha
                score = np.sum(self.iterate_score(count=count, iter_opts=iter_opts))
                if score > max_score:
                    max_score = score
                annotations[commit.hexsha] = score

        def scale(x):
            x = float(x)
            return (np.exp(x/max_score) - 1) / (np.exp(1)-1)

        for commit, score in annotations.items():
            annotations[commit] = (scale(score), str(score))

        annotate(output=os.path.join(self.project_dir,output), repo=self.project_dir, annotate=annotations, branches=branches)


#print t.iterate_score(10,params={'x':1,'y':1.0000000149011612})
# print t.optimise(['x','y'],count=1,params={'x':1,'y':1})


# Something like this will find the first commit:
#
# x = Repo('.')
# print list(x.get_walker(include=[x.head()]))[-1].commit
#
# (Note that this will use O(n) memory for large repositories, use an iterator to get around that)



# Using pure Git-Python, it can also be done. I have not found a way to identify a set of kwargs that would do it in one go either. But one can simply construct a set of shas of the master branch, then use iter_commits on the to-be-examined branch in order to find the first one that doesn't appear in the parent:
#
# from git import *
#
# repo_path = '.'
# repo = Repo(repo_path)
# parent_branch = repo.branches.master
# examine_branch = repo.branches.test_feature_branch
#
# other_shas = set()
# for parent_commit in repo.iter_commits(rev=parent_branch):
#     other_shas.add(parent_commit.hexsha)
# for commit in repo.iter_commits(rev=examine_branch):
#     if commit.hexsha not in other_shas:
#         first_commit = commit
#
# print '%s by %s: %s' % (first_commit.hexsha[:7],
#         first_commit.author.name, first_commit.summary)
#
# And if you really want to be sure to exclude all commits on all other branches, you can wrap that first for-loop in another for-loop over repo.branches:
#
# other_shas = set()
# for branch in repo.branches:
#     if branch != examine_branch:
#         for commit in repo.iter_commits(rev=branch):
#             other_shas.add(commit.hexsha)
#
#     Caveat 1: the 2nd approach shows the first commit that does not appear on any other branch, which is not necessarily the first commit on this branch. If feat_b is branched off from feat_a, which comes from master, then this will show the first commit on feat_a after feat_b has been branched off: the rest of feat_a's commits are already on feat_b.
#     Caveat 2: git rev-list and both of these solutions only work as long as the branch isn't merged back into master yet. You're literally asking it to list all commits on this branch but not on the other.
#     Remark: the 2nd approach is overkill and takes a fair bit more time to complete. A better approach is to limit the other branches to a list of known merge branches, should you have more than just master.
#

#t = Tester('defense',MarathonComputation)
#print plot_progress(t)
#
# with Tester('defense',MarathonComputation) as t:
#
#     print t.iterate_score(count=2)
#
#     t.ref='lazy_build'
#
#     print t.iterate(count=2)
