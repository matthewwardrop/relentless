
#include <cstdlib>
#include <cstdio>
#include <iostream>
#include <iomanip>
#include <cstring>
#include <cmath>
#include <limits>

extern char **environ;

using namespace std;

typedef numeric_limits <double> dbl;




void print_env() {
  char *s = *environ;

  for (int i=1; s; i++) {
    printf("%s\n", s);
    s = *(environ+i);
  }
}

long getparam(const char* env, long default_value) {
  const char *env_value = getenv(env);
  if (env_value == NULL) {
    return default_value;
  }
  return strtol(env_value, (char**) NULL, 10);
}

double getparam(const char* env, double default_value) {
  const char *env_value = getenv(env);
  if (env_value == NULL) {
    return default_value;
  }
  return strtod(env_value, (char**) NULL);
}

struct Parameters {

};

int main() {
  cout.precision(dbl::digits10);
  bool DEBUG = getparam("DEBUG",(long)0) > 0;
  double x = getparam("RELENTLESS_x",1.0);
  double y = getparam("RELENTLESS_y",1.0);

  cout << "Score = " << setprecision(dbl::digits10) << pow(x,2.) + pow(y,2.) << endl;
  cout << "x = " << x << endl;
  cout << "DEBUG = " << DEBUG << endl;

  return 0;
}
