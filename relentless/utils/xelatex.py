
import subprocess
import tempfile
import os
import shutil

class XeLaTeX(object):

	def __init__(self, output, **kwargs):
		self.tmpdir = tempfile.mkdtemp()

		self.dest = output

		self.process(**kwargs)

		self.compile()

	def process(self, **kwargs):
		raise NotImplementedError()

	@property
	def output(self):
		if getattr(self,'_output',None) is None:
			self._output = open(os.path.join(self.tmpdir, 'output.tex'),'w')
		return self._output

	def compile(self):
		self._output.close()
		process = subprocess.Popen(['xelatex','output'], cwd=self.tmpdir)
		if process.wait() == 0:
			shutil.copyfile(os.path.join(self.tmpdir, 'output.pdf'), self.dest+".pdf")
