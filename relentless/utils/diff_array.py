import os
import subprocess
import math
import numpy as np
from .xelatex import XeLaTeX

class DiffArray(XeLaTeX):

	def template(self):
		with open(os.path.join(os.path.dirname(__file__),'templates','diff_array.tex')) as f:
			return f.read()

	def process(self, output='diff', new=None, old=None, tasks=None, columns=None, maximise=True):

		if new is None or old is None:
			raise ValueError("new and old must both be numpy arrays of the same dimension")

		output = {}

		lnew = new.flatten()
		lold = old.flatten()

		diffs = []
		r = new - old
		it = np.nditer(r, flags=['f_index'])
		while not it.finished:
			diffs.append( (it.index, float(it[0]) ) )
			it.iternext()

		if columns is None:
			columns = int(np.ceil(np.sqrt(len(diffs))))

		total_new = np.sum(new)
		total_old = np.sum(old)

		if total_old == 0:
			total_old = 1

		wins = np.sum(r>0)
		losses = np.sum(r<0)
		LOS = 0.5*(1+math.erf( float(wins - losses)/math.sqrt(wins+losses)/math.sqrt(2) ))

		max_diff = np.max(np.abs(r))
		if maximise:
			max_improvement = np.max(r)
			max_regression = np.min(r)
			avg_improvement = np.average(r)
		else:
			max_improvement = np.max(-r)
			max_regression = np.min(-r)
			avg_improvement = np.average(-r)

		if tasks is None:
			tasks = range(1, len(diffs)+1)

		output['summary'] = r"""	\node[rectangle, align=center] at (%.1f, 1) {Best: %.3f | Worst: %.3f | Avg: %.3f | Rel: %.3f \\ Wins: %d | Losses: %d | LOS: %.3f};""" % (float(columns-1)/2, max_improvement, max_regression, avg_improvement, float(total_new)/float(total_old), wins, losses, LOS)

		output['elements'] = []
		for count, (index, rel) in enumerate(diffs):
			rel /= max_diff
			if type(index) != tuple:
				index = (index - (index/columns)*columns, -(index/columns))
			index = map(str,index)
			textcolor = "black" # "white" if abs(rel) > 0.5 else
			if maximise:
				bgcolor = "green" if rel >=0 else "red"
			else:
				bgcolor = "red" if rel >=0 else "green"
			output['elements'].append(r"""	\node[commit, %s, fill=%s!%s] at (%s) {\adjsizetonode{
				{\fontsize{5}{5}\selectfont %.2f\par}
				{\fontsize{12}{12}\selectfont\bf %d\par}
				{\fontsize{5}{8}\selectfont %.2f\par}
			}};""" % (textcolor, bgcolor, round(abs(rel)*100), ','.join(index), lnew[count], tasks[count], lold[count]) )
		output['elements'] = '\n'.join(output['elements'])

		return output
