#define _GNU_SOURCE 1

#include <stdio.h>
#include <sys/types.h>
#include <fcntl.h>
#include <dirent.h>

#define NAME	"O_CLOEXEC-vs-O_ATOMICLOOKUP"

DIR *opendir(const char *name)
{
  int fd = open(name, O_RDONLY|O_NDELAY|O_DIRECTORY|O_LARGEFILE);
  if (fd == -1)
    return NULL;
  return fdopendir(fd);
}
