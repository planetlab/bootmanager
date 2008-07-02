#define _GNU_SOURCE 1

#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>
#include <sys/types.h>
#include <fcntl.h>
#include <dirent.h>
#include <glob.h>
#include <stdarg.h>
#include <string.h>

#define INIT(x)	real_ ## x = dlsym(RTLD_NEXT, #x); \
		if (!real_ ## x) { \
		  fprintf(stderr, "Would the real " #x " please stand up? %s\n", dlerror()); \
		  exit(1); \
		}

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

static int (*real_glob)(const char *pattern, int flags,
         int (*errfunc) (const char *epath, int eerrno),
         glob_t *pglob);

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
  if (!real_glob) {
    INIT(glob)
  }
  return real_glob(pattern, flags, errfunc, pglob);
}

#define PWD_LOCKFILE "/etc/.pwd.lock"

static int lock_fd = -1;

/* FIXME: Ignores multi-thread issues.
 *        Doesn't wait for the file to become lockable
 */
int lckpwdf(void)
{
  struct flock fl = { 0 };

  /* This process already holds the lock */
  if (lock_fd != -1)
    return -1;

  lock_fd = open(PWD_LOCKFILE, O_WRONLY|O_CREAT, 0600);
  if (lock_fd == -1)
    return -1;

  if (fcntl(lock_fd, F_SETFD, fcntl(lock_fd, F_GETFD, 0) | FD_CLOEXEC) == -1) {
    close(lock_fd);
    return -1;
  }

  fl.l_type = F_WRLCK;
  fl.l_whence = SEEK_SET;
  return fcntl(lock_fd, F_SETLKW, &fl);
}

int ulckpwdf(void)
{
  int result;

  if (lock_fd == -1)
    return -1;

  result = close(lock_fd);
  lock_fd = -1;
  return result;
}

static (*real_open)(const char *name, int flags, ...);
int open(const char *name, int flags, ...)
{
  mode_t mode;
  if (flags & O_CREAT) {
    va_list va;
    va_start(va, flags);
    mode = va_arg(va, mode_t);
    va_end(va);
  }
  if (!real_open) {
    INIT(open)
  }
  return real_open(name, flags, mode);
}

static FILE *(*real_fopen)(const char *name, const char *flags);
FILE *fopen(const char *name, const char *flags)
{
  char *str, *ptr = strchr(flags, 'e');
  FILE *ret;
  if (ptr) {
    str = strdup(flags);
    ptr = (str + (ptr - flags));
    strcpy(ptr, ptr + 1);
  }
  else
    str = flags;
  if (!real_fopen) {
    INIT(fopen)
  }
  ret = real_fopen(name, str);
  if (ptr)
    free(str);
  return ret;
}

static void _init() __attribute__((constructor));
static void _init()
{
  INIT(glob)
  INIT(open)
  INIT(fopen)
}
