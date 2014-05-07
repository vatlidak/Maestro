'''
Implementation of semantic actions
'''
from networkx import DiGraph
import subprocess
import time
import os


def isCyclicUtil(graph, vertex, visited, recstack):

    if not visited[vertex]:
        visited[vertex] = True
        recstack[vertex] = True
    for des in graph.successors(vertex):
        if not visited[des] and isCyclicUtil(graph, des, visited, recstack):
            return True
        elif recstack[des]:
            return True
    recstack[vertex] = False
    return False


def isCyclic(graph):

    visited = {}
    recstack = {}
    for node in graph.nodes():
        visited[node] = False
        recstack[node] = False
    for node in graph.nodes():
        if isCyclicUtil(graph, node, visited, recstack):
            return True
    return False


depen_graph = DiGraph()


class Job():
    '''Constructor of class should be supplied with job name and
    respective script name
    '''
    def __init__(self, script, arguments=[]):
        self._dependencies = []
#        self._workers = workers
        self._script = script
        self._arguments = arguments
        self._stderr = None
        self._stdout = None
        self._errno = None  # errno is None since job has not run
        argu = '_'.join(arguments)
        depen_graph.add_node(self)
        # create log file; truncate it if it exists
        self._logfile_name = os.getcwd() +\
                             '/' + self._script +\
                             "_" + argu
        self.f = open(self._logfile_name, "w")
        self.f.close()

    def stdout(self):
        return self._stdout

    def perror(self):
        return self._errno, self._stderr

    def add_dependency(self, depends_on):
        '''Add names of jobs on which current object
        depends on.
        '''
        for job in depends_on:
            self._dependencies.append(job)
            depen_graph.add_edge(self, job)

    def run(self):
        '''this should do the remote execution of scripts'''
        # need error checkong of what Popen returns
        try:
            arg =" ".join(self._arguments)
            args = arg.replace('"', '')
            script = self._script.replace('"', '')
            all = script + " " + args
            s = subprocess.Popen(all, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            self._stdout, self._stderr = s.communicate()
            self._errno = s.returncode
            #self._log()
        except Exception, error:
            print "Unhandled Exception:", error
            return

    def can_run(self):
        '''check if dependencies are fullfilled.
        Current instrance can run only if all jobs from
        its dependency list have successed ( errno is zero )
        '''
        if not self._dependencies:
            return True
        for job in self._dependencies:
            if job.perror()[0] != 0:
                return False
        return True

    def _log(self):
        # file is created by class constructor. Append logs.
        f = open(self._logfile_name, "a")
        print >> f, "STDOUT:"
        print >> f, self.stdout
        print >> f, "STDERR:"
        print >> f, self.stderr
        print >> f, "---------"
        f.close()


class JobQueue:
    '''Construct job queue as a list whose first element
    are job names of jobs with zero dependencies,
    second are job names of jobs with one dependency, etc.
    '''
    def __init__(self,  MaxDependencies=10):
        self.Q = []
        for _ in range(MaxDependencies):
            self.Q.append([])

    def enqueue(self, job, dependencies):
        self.Q[dependencies] = job


def add_dependencies(jobs, depend_on):
    for job in jobs:
        job.add_dependency(depend_on)


def run(Queue):
    '''Try to run job from queue'''
    # suppose queue is constructed.
    #
    # e.g. Q = [[a,b],[c]], means that jobs with one
    # dependency i.e., Q[0] = [a,b] should run before
    # jobs with two dependencies, i.e., Q[1] = [c]
    #
    if isCyclic(depen_graph):
        print "Your jobs have circular dependencies"
        return False
    while Queue:
        for job in Queue:
            if job.can_run():
                Queue.remove(job)
                job.run()
                (error, error_str) = job.perror()
                if (error != 0):
                    print job.stdout()
                else:
                    print error_str
        time.sleep(0.5)
