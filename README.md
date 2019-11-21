# joplintool

joplintool by pat (based upon work from foxmask and tessus)

  - checks and removes orphaned files in local resourcedir and remote sync dir
  - default is a dryrun, nothing will be deleted
  - removal of orphanes ignores timestamps...

  - use --force if you know what you are doing
  - EXPORT A BACKUP BEFORE USE !

optional arguments:
  -h, --help                    show this help message and exit
  -checkr, --checkresource s    checks for orphanes files in resourcedir
  -checkd, --checkdropbox       checks for orphanes files in dropboxdir
  -force, --force               enables delete for checkorphanes and checkdropbox
  -r, --recurse                 recurses through folders and notes / shows tree
  -a, --align                   deflate/pack db after data was deleted...
  -i, --info                    shows how many notes, folders, imagerefs are stored in the db
