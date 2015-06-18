
import subprocess
import tempfile
import os
import shutil

class XeLaTeX(object):

	def __init__(self, output, **kwargs):
		self.tmpdir = tempfile.mkdtemp()

		self.dest = output

		self.output( self.template() % self.process(**kwargs) )

		self.compile()

	def template(self):
		raise NotImplementedError()

	def process(self, **kwargs):
		raise NotImplementedError()

	def output(self, content):
		f = open(os.path.join(self.tmpdir, 'output.tex'),'w')
		f.write(content)
		f.close()

	def compile(self):
		process = subprocess.Popen(['xelatex','output'], cwd=self.tmpdir)
		if process.wait() == 0:
			shutil.copyfile(os.path.join(self.tmpdir, 'output.pdf'), self.dest+".pdf")
		#shutil.rmtree(self.tmpdir)
