# joplintool


joplintool 0.9.2 (for [joplin](https://joplinapp.org/)) by pat (based upon work from foxmask and tessus)

  - checks and removes orphaned files in local resourcedir and remote sync dir
  - shows some stats and a tree of your database
  - default is a dryrun, nothing will be deleted
  - removal of orphanes ignores timestamps...
  - removal in resourcedir uses webinterface
  - use --force if you know what you are doing
  - EXPORT A BACKUP BEFORE USE !

### optional arguments:

  -checkr, --checkresources     checks for orphanes files in resourcedir

  -checkd, --checkdropbox       checks for orphanes files in dropboxdir

  -force, --force               enables delete for checkorphanes and checkdropbox

  -r, --recurse                 recurses through folders and notes / shows tree

  -a, --align                   deflate/pack db after data was deleted...

  -i, --info                    shows how many notes, folders, imagerefs are stored in the db

### checkdropbox option
- checks if md files in sync dir can be found in database (note, folder, tag) of resourcedir (images)
- if not found they will be removed with the --force option

### checkresource option
- checks if all files in resourcedir are assocciated with any note)
- does NOT consider timestamps ...
- if not found they will be removed with the --force option

*used sql query:*
```
            SELECT resource_id FROM note_resources  
            WHERE is_associated = 0 and resource_id not in 
               (SELECT resource_id FROM note_resources 
                WHERE is_associated = 1) 
            ORDER BY resource_id
```
