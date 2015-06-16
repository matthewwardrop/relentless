import subprocess

import scipy.optimize as spo

import sys, os, re, time, git, shelve, shutil

import parampy, numpy as np

from .computations import *

from multiprocessing import Lock

import tempfile

import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
from mplstyles import SampleStyle, contour_image


class Tester(object):

    computation_types = {
        'simple': SimpleComputation,
        'SimpleComputation': SimpleComputation,
        'marathon': MarathonComputation,
        'MarathonComputation': MarathonComputation
    }

    def __init__(self, project, computation_type=None, computation_wrapper=None, working_dir='_relentless', cache=True, auto_profile=True, **kwargs):
        self.project = os.path.basename(project)
        self.project_dir = os.path.abspath(os.path.dirname(project))
        self.working_dir = working_dir
        if not os.path.exists(self.path("")):
            os.makedirs(self.path(""))

        if auto_profile:
            self.config = self.load_config()
        else:
            self.config = {}

        self.__set_attribute('computation_type', computation_type, default=SimpleComputation)

        if type(self.computation_type) is str:
            try:
                self.computation_type = self.computation_types[self.computation_type]
            except:
                raise ValueError("Invalid computation type: %s" % self.computation_type)
        if not issubclass(self.computation_type, Computation):
            raise ValueError("Invalid computation_type provided.")

        self.__set_attribute('computation_wrapper',computation_wrapper)

        self.lock = Lock()
        self.p = parampy.Parameters()

        self.__kwargs = kwargs

        self.init(**kwargs)

        self.save_config()


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
        return self.computation_type(self.project, working_dir=self.project_dir, wrapper=self.computation_wrapper)

    def cleanup(self):
        self._computation = None
        self._cleanup()

    def _cleanup(self):
        pass

    def run(self,task=0,params={},print_info=False):
        task = int(task)
        result = self.cache(task=task, params=params)
        if result is None:
            result = self.cache(value=self.computation.run(task,params),task=task,params=params)
        if print_info:
            for item in result.info.items():
                print "%s: %s" % item
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

    def __prepare_iterate(self, tasks, params={}):
        # Make sure we have compiled before the fork in ranges_iterator
        for task in tasks:
            if self.cache(task=task, params=params) is None:
                self.computation
                return

    def iterate(self,count=1,tasks=None,ranges=None,params={},iter_opts={}):
        if ranges is None:
            ranges = []
        def f(params):
            task = int(params.pop('task'))
            return self.run(task=task, params=params)
        if type(ranges) is dict:
            ranges = [ranges]
        tasks = self.__tasks(count, tasks)
        ranges.insert(0,{'task':tasks})
        self.__prepare_iterate(tasks, params=params)
        iterator = self.p.ranges_iterator(ranges, params=params, function=f, **iter_opts)
        results = np.empty(iterator.ranges_eval.shape, dtype=object)
        for index,data in iterator:
            results[index] = data
        return results

    def plot_dependence(self, output="dependence", **kwargs):
        ranges = kwargs.get('ranges',[])
        if len(ranges) == 0:
            raise ValueError("Need to iterate over some value.")

        results = np.sum(self.iterate_score(**kwargs),axis=0)
        style = SampleStyle()
        with style:
            if len(results.shape) == 1:
                var = ranges[1].keys()[0]
                xs = self.p.range(var, **ranges[0])
                plt.plot([xs, results])
                plt.xlabel(var)
            elif len(results.shape) == 2:
                var_x = ranges[1].keys()[0]
                var_y =  ranges[2].keys()[0]
                xs = self.p.range(var_x, **ranges[1])
                ys = self.p.range(var_y, **ranges[2])
                contour_image(xs, ys, results, cguides=True, label=True, cmap=plt.get_cmap('hsv'))
                plt.xlabel(var_x)
                plt.ylabel(var_y)
            else:
                raise ValueError("Cannot plot more than 2 dimensions.")
            style.savefig(os.path.join(self.project_dir,output+".pdf"))

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

    def save_config(self):
        s = shelve.open(self.path('tester_init.config'), protocol=0)
        s['config'] = self.config
        s.close()

    def load_config(self):
        s = shelve.open(self.path('tester_init.config'), protocol=0)
        config = s.get('config',{})
        s.close()
        return config

    def __set_attribute(self, attr, value, default=None):
        if value is None:
            value = self.config.get(attr,default)
        setattr(self, attr, value)
        self.config[attr] = value

class GitTester(Tester):

    def init(self, ref='master'):
        self.__project_repo = git.Repo(self.project_dir)
        self.ref = ref

    @property
    def ref(self):
        return self.__ref
    @ref.setter
    def ref(self, ref):
        self.cleanup()
        self.__ref = ref

    def get_repo_dir(self):
        if getattr(self,'_repo_path',None) is None:
            self._repo_path = tempfile.mkdtemp()
        return self._repo_path # self.path('checkout')#self.path(self.ref)

    def get_cache_key(self, task=0, params={}):
        ref = str(self.__project_repo.commit(self.ref).hexsha)
        return '%s_%d'%(ref,task)

    def __get_ref(self, repo, ref):
        try:
            repo.commit(ref)
            return ref
        except:
            return repo.commit('origin/'+ref).hexsha

    def get_computation(self):
        d = self.get_repo_dir()
        if os.path.exists(d) and os.path.exists(os.path.join(d,'.git')):
            self.__repo = git.Repo(d)
            self.__repo.remotes.origin.pull()
        else:
            self.__repo = git.Repo(self.project_dir).clone(d)
        self.__repo.git.checkout(self.__get_ref(self.__repo, self.ref))
        return self.computation_type(self.project, working_dir=d, src_dir=self.project_dir, wrapper=self.computation_wrapper)

    def _cleanup(self):
        if getattr(self, '_GitTester__ref', None) is not None:
            d = self.get_repo_dir()
            _repo_path = None
            if os.path.exists(d):
                shutil.rmtree(d)

    def annotate_commits(self, count=1, output='history', branches=None, since=None, iter_opts={}):
        from .utils.git_history import GitAnnotate, get_commits_by_branch

        annotations = {}
        branches, commits, all_commits = get_commits_by_branch(repo=self.project_dir, branches=branches)

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

        GitAnnotate(output=os.path.join(self.project_dir,output), repo=self.project_dir, annotate=annotations, branches=branches)

    def compare(self, ref, base='master', output="diffs_", count=1,fields=['score'],tasks=None,params={},iter_opts={}):
        from .utils.plot_diff import PlotDiff

        self.ref = ref
        results_new = self.iterate(count=count, tasks=tasks, params=params, iter_opts=iter_opts)
        self.ref = base
        results_old = self.iterate(count=count, tasks=tasks, params=params, iter_opts=iter_opts)

        def get_map(field):
            def f(a):
                try:
                    return a.info[field]
                except:
                    return getattr(a,field)
            return np.vectorize(f)

        tasks = get_map('task')(results_new).flatten().tolist()

        for field in fields:
            PlotDiff(output=os.path.join(self.project_dir, output+field), new=get_map(field)(results_new).astype(float), old=get_map(field)(results_old).astype(float), tasks=tasks, maximise=field not in ComputationResult.minimise)


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
