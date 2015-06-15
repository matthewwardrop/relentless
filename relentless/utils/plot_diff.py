import os
import subprocess
import numpy as np

def plot_diff(output='diff', new=None, old=None, tasks=None, columns=10, maximise=True, cwd=None):

	if new is None or old is None:
		raise ValueError("new and old must both be numpy arrays of the same dimension")

	f = open(output+'.tex','w')

	header = r"""
	\documentclass{standalone}
	\usepackage{tikz}
	\usepackage{fancyvrb}
	\usetikzlibrary{calc}
	\usetikzlibrary{positioning}
	\usepackage{filecontents}

	\usepackage{adjustbox}
	\newcommand{\adjsizetonode}{%
	  \adjustbox{varwidth={5cm}\centering,keepaspectratio,clip=true,max totalsize={.8\dimexpr\pgfkeysvalueof{/pgf/minimum width}\relax}{.8\dimexpr\pgfkeysvalueof{/pgf/minimum height}\relax}}%
	}

	\begin{document}

		\begin{tikzpicture}
			\tikzstyle{commit}=[draw,rectangle,fill=blue!80,inner sep=0pt,minimum width=0.9cm,minimum height=0.9cm,inner sep=1mm, rounded corners=3pt, align=center]
		"""

	middle = r"""
		\end{tikzpicture}
	"""

	footer = """
	\end{document}
	"""

	lnew = new.flatten()
	lold = old.flatten()

	f.write(header)

	diffs = []
	r = new - old
	it = np.nditer(r, flags=['f_index'])
	while not it.finished:
		diffs.append( (it.index, float(it[0]) ) )
		it.iternext()

	max_diff = 1.0
	max_improvement = 0
	max_regression = 0
	avg_improvement = 0

	if tasks is None:
		tasks = range(1, len(diffs)+1)

	for (index, rel) in diffs:
		rel = float(rel)
		if maximise:
			max_improvement = rel if max_improvement < rel else max_improvement
			max_regression = rel if max_regression > rel else max_regression
		else:
			max_improvement = rel if max_improvement > rel else max_improvement
			max_regression = rel if max_regression < rel else max_regression
		max_diff = abs(rel) if abs(rel) > max_diff else max_diff
		avg_improvement += rel
	avg_improvement /= len(diffs)

	f.write(r"	\node at (%.1f, 1) {Best: %.3f | Worst: %.3f | Avg: %.3f};" % (float(columns-1)/2, max_improvement, max_regression, avg_improvement))

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
		f.write(r"""	\node[commit, %s, fill=%s!%s] at (%s) {\adjsizetonode{
			{\fontsize{5}{5}\selectfont %.2f\par}
			{\fontsize{12}{12}\selectfont\bf %d\par}
			{\fontsize{5}{8}\selectfont %.2f\par}
		}};""" % (textcolor, bgcolor, round(abs(rel)*100), ','.join(index), lnew[count], tasks[count], lold[count]) )

	f.write(middle)

	f.write(footer)

	f.close()

	if cwd is None:
		cwd = os.path.dirname(output)
	subprocess.Popen(['xelatex',output], cwd=cwd).wait()
