#define _GNU_SOURCE 1

#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>
#include <sys/types.h>
#include <fcntl.h>
#include <dirent.h>
#include <glob.h>

static int (*real_glob)(const char *pattern, int flags,
         int (*errfunc) (const char *epath, int eerrno),
         glob_t *pglob);

DIR *opendir(const char *name)
{
  int fd = open(name, O_RDONLY|O_NDELAY|O_DIRECTORY|O_LARGEFILE);
  if (fd == -1)
    return NULL;
  return fdopendir(fd);
}

DIR *__opendir(const char *name)
{
  return opendir(name);
}

int glob(const char *pattern, int flags,
         int (*errfunc) (const char *epath, int eerrno),
         glob_t *pglob)
{
  if (!(flags & GLOB_ALTDIRFUNC)) {
    pglob->gl_closedir = closedir;
    pglob->gl_readdir = readdir;
    pglob->gl_opendir = opendir;
    pglob->gl_lstat = lstat;
    pglob->gl_stat = stat;
    flags |= GLOB_ALTDIRFUNC;
  }
  return real_glob(pattern, flags, errfunc, pglob);
}

static void _init() __attribute__((constructor));
static void _init()
{
  real_glob = dlsym(RTLD_NEXT, "glob");
  if (!real_glob) {
    fprintf(stderr, "Would the real glob please stand up? %s\n", dlerror());
    exit(1);
  }
}
