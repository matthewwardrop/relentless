#objects := $(patsubst %.cpp,%.o,$(wildcard *.cpp))

all: $(basename $(wildcard *.cpp)) $(basename $(wildcard *.c))

% : %.cpp
	clang++ -g -o $@ $<

% : %.c
	clang -g -o $@ $<

#soln : $(objects)
#	clang++ -o soln $(objects)
