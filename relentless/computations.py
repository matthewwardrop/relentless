import os
import re
import subprocess
import time
from multiprocessing import Lock, Value
from abc import abstractmethod, ABCMeta

class Computation(object):

    def __init__(self, project, working_dir=".", src_dir=None, **kwargs):
        self.project = project
        self.working_dir = os.path.abspath(working_dir)
        if src_dir is None:
            src_dir = self.working_dir
        self.src_dir = os.path.abspath(src_dir)
        self.compiled=Value('i',0)
        self.lock = Lock()
        self.init(**kwargs)

    def init(self):
        pass

    def compile(self):
        with self.lock:
            if not self.compiled.value > 0:
                self._compile()
                self.compiled.value=1

    def _compile(self):
        raise NotImplementedError()

    def run(self, task=0, params={}):
        raise NotImplementedError()

    def process_result(self, result):
        for m in re.finditer('([A-Za-z0-9 ]+) = ([A-Za-z0-9]+)', result.stdout+result.stderr):
            gs = m.groups()
            result.info[gs[0].lower()] = gs[1]
        return result

    def _run(self, task, params, *args, **kwargs):
        if not self.compiled.value > 0:
            self.compile()
        defaults={'stdout':subprocess.PIPE, 'stderr':subprocess.PIPE}
        defaults.update(kwargs)
        t = time.time()
        p = subprocess.Popen(*args, **defaults)
        stdout, stderr = p.communicate()
        result = ComputationResult(task, params, runtime=time.time()-t, stdout=stdout, stderr=stderr)
        result(returncode=p.returncode)
        if result.returncode != 0:
            print result.stdout
            print result.stderr
        return self.process_result(result)

class SimpleComputation(Computation):

    def init(self, wrapper=None, wrapper_vis=None):
        self.wrapper = wrapper
        self.wrapper_vis = wrapper_vis

    def _compile(self):
        f = open(os.path.join(self.working_dir, 'compile.log'),'w')
        if os.path.exists(os.path.join(self.working_dir, 'Makefile')):
            subprocess.Popen(["make",os.path.basename(self.project)],cwd=self.working_dir, stdout=f, stderr=f)
        else:
            compile = subprocess.Popen(["make","-f",os.path.join(os.path.dirname(os.path.abspath(__file__)),'Makefile'),os.path.basename(self.project)],cwd=self.working_dir, stdout=f, stderr=f)
        compile.wait()
        f.close()
        if compile.returncode != 0:
            raise RuntimeError("Code did not compile successfully. See the compile.log in the source tree at %s." % os.path.join(self.working_dir, 'compile.log'))

    def run(self,task=0,vis=False,params={}):
        env = os.environ.copy()
        for variable in params:
            env["RELENTLESS_%s" % variable] = str(params[variable])

        wrapper = self.wrapper
        if vis and self.wrapper_vis is not None:
            wrapper = self.wrapper_vis

        if wrapper is None:
            cmd = [os.path.join(self.working_dir, self.project)]
        else:
            command = wrapper % {  'project': os.path.join(self.working_dir, self.project),
                                        'src_dir': self.src_dir,
                                        'working_dir': self.working_dir,
                                        'task': task}
            cmd = command.split()

        return self._run(task, params, cmd, env=env, cwd=self.working_dir)


class MarathonComputation(SimpleComputation):

    def init(self, wrapper=None, wrapper_vis=None):
        if wrapper is None:
            wrapper = "java -jar %(src_dir)s/tester.jar -exec %(project)s -seed %(task)s -novis"
        if wrapper_vis is None:
            wrapper_vis = "java -jar %(src_dir)s/tester.jar -exec %(project)s -seed %(task)s"
        self.wrapper = wrapper
        self.wrapper_vis = wrapper_vis

class ComputationResult(object):

    minimise = ['runtime']

    def __init__(self, task, params, stdout, stderr, runtime):
        self.info = {}
        self(stdout=stdout,
            stderr=stderr,
            params=params,
            task=task,
            runtime = runtime)

    def __call__(self, *args, **kwargs):
        for key, value in kwargs.items():
            self.info[key] = value
        r = []
        for arg in args:
            return self.info[arg]

    def __getattr__(self, key):
        if key != 'info' and key in self.info:
            return self.info[key]
        raise AttributeError()

    @property
    def score(self):
        if 'score' in self.info:
            return float(self.info['score'])
        return -1
        #raise ValueError("No score available in the info dictionary.")

    def __str__(self):
        return "<ComputationResult with score %f>" % self.score

    def __repr__(self):
        return str(self)

    def pretty_print(self):
        from utils.console import getTerminalSize
        width,height=getTerminalSize()

        sep = "-"*width
        print sep
        print " Task %d" % self.task
        print sep
        if len(self.info.get('params')) > 0:
            for key,value in self.info['params']:
                print " %s: %s" % (key, value)
            print "-"*width

        info_keys = self.info.keys()


        for key in ["score", "runtime"]:
            if key in self.info:
                print " - %s: %s" % (key, self.info[key])
                info_keys.remove(key)

        print " Other Information:"
        for key in info_keys:
            if key in ["params","returncode","task","stdout","stderr"]:
                continue
            print "   - %s: %s" % (key, self.info[key])

        if self.info.get('returncode',0) != 0:
            print "\nERROR: Return code was %d" % self.info['returncode']
            if self.info.get('stdout',"").strip() != "":
                print sep[:width/2-4] + " STDOUT " + sep[width/2+4:]
                print self.info.get('stdout').strip()
                print
            if self.info.get('stderr',"").strip() != "":
                print sep[:width/2-4] + " STDERR " + sep[width/2+4:]
                print self.info.get('stderr').strip()
                print

        print sep
