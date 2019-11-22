# encoding: utf-8
# needs python3

import os, sys,  argparse

try:
    import asyncio, sqlite3, configparser
except:
    print('needs python3... sorry ')
    exit()

from os.path import join

try:
    from joplin_api import JoplinApi

except ImportError:
    print('joplin api is not installed.\nplease run: pip install joplin-api')
    exit()

class JoplinHelper():
    
    def __init__(self):
        try:
            self.orphanes = []
            
            conf_file_abspath = join(os.path.dirname(__file__),'joplintool.conf')
            config = configparser.ConfigParser()
            
            if config.read(conf_file_abspath) == []:
                with open(conf_file_abspath,'w') as f:
                    f.writelines(['[paths]\n',
                                 'path_joplin  = c:\_office_\Joplin\n',
                                 'path_Dropbox = f:\_Archive_\Dropbox\Apps\Joplin\n',
                                 '\n[misc]\n',
                                 'token = xxxxxxxxxxxxxxxxxxxxxxxxxxxx #insert token here\n'
                                 ])
                raise BaseException('could not find joplintool.conf\ncreating new config file\nplease edit paths etc. in config file')
            
            self.path_joplin   = config['paths']['path_joplin'].strip('\'\"')    # strip '' and "" from strings
            self.path_Dropbox  = config['paths']['path_dropbox'].strip('\'\"')
            self.path_db       = join(self.path_joplin, 'JoplinProfile', 'database.sqlite') 
            self.path_resources= join(self.path_joplin, 'JoplinProfile', 'resources')
            if not os.path.exists(self.path_db):
                raise BaseException('wrongs paths ... check joplintool.conf')
            
            self.joplin = JoplinApi(token = config['misc']['token'])

            asyncio.run(self.joplin.ping())    # raises exception if it cannot connect to web clipper
      
            self.cursor = sqlite3.connect(self.path_db).cursor()

        except ConnectionRefusedError:
            print('cannot connect to web clipper....\nis joplin running ?\nalso check token in conf file')
            
        except BaseException as err:
            print(err)
            print('exiting...')
            exit()
            
    
    def recurse_folders(self, folderlist = None , recursion_level=0):
    
        def show_notes(d, recursion_level, folder_id):
            res = asyncio.run(self.joplin.get_folders_notes(folder_id))
            for d in res.json():
                print('{} {} \t({})'.format(' ' * 4 * recursion_level, d['title'] , d['id']))
    
        if folderlist == None:
            res = asyncio.run(self.joplin.get_folders())
            folderlist = res.json()
        
        for d in folderlist:
            print('\n{} {} \t({})'.format('-' * 4 * recursion_level, d['title'] , d['id']))
            show_notes(d, recursion_level, d['id'])
            if 'children' in d:
                recursion_level +=1
                self.recurse_folders(d['children'],recursion_level = recursion_level)

                
    def sql_get_orphanes(self, verbose=False):
        orphanes = []
        
        cmd = '''
            SELECT resource_id FROM note_resources  
            WHERE is_associated = 0 and resource_id not in 
               (SELECT resource_id FROM note_resources 
                WHERE is_associated = 1) 
            ORDER BY resource_id
        '''
        #group by resource_id having max(last_seen_time) < strftime('%s','now','-${KEEP} days')*1000" >$TMPFILE  # time not considered... #not used
        
        if verbose:
            print('orphanes from sql database:')
        for l in self.cursor.execute(cmd): 
            id = l[0]
            orphanes.append(id)
            if verbose:
                print (id)
        
        return orphanes
    
    def info(self):
        notes = len(self.sql_get_notes() )
        folders = len(self.sql_get_folders() )
        images =  len(self.sql_get_resources() )
        tags = len (self.sql_get_tags() )
        
        files_resource = [f for f in os.listdir(self.path_resources) if os.path.isfile(join(self.path_resources, f))]
        len_files_in_resourcedir = sum( [os.path.getsize(join(self.path_resources,f)) for f in files_resource ] ) # get sum of all filesizes
        
        print('\ninfo (data in database):')
        print('-----------------------')
        print('notes:   ', notes)
        print('folders: ', folders)
        print('images:   {}  ({:,} bytes)'.format(images, len_files_in_resourcedir, len(files_resource) ) )
        print('tags:    ', tags)
        print('total:   ', notes + folders + images +tags)
        #print('\ntotal size of images in resourcedir: {:,} bytes in {} images'.format(len_files_in_resourcedir, len(files_resource)))
        
        
    def check_resources(self, do_delete=False):    
        # delete orphaned files from resource
        self.orphanes = self.sql_get_orphanes()
        print('\nchecking for orphanes (files in resourcedir not assocciated with any note):')
        print('-------------------------------------------------------------------------')

        if self.orphanes == []:
            print('found none ... good')
        else:
            for fname in self.orphanes:
                print('not_associated: ', (fname))
        
        if do_delete and self.orphanes != []:
            self.del_orphanes()
        
        print ('\nchecking for additional files in resourcedir which are not in the database:')    # not sure if is of concern ...
        files_resource = [f for f in os.listdir(self.path_resources) if os.path.isfile(join(self.path_resources, f))]
        
        files_db = self.sql_get_resources()
        files_additional = [f for f in files_resource if f not in files_db]

        if files_additional == []:
            print('found none ... good')
        else:
            for f in files_additional:
                print(f)
                if do_delete:
                    os.remove(join(self.path_resources,f))
                    print('deleted...')
        
    def del_orphanes(self):
        for fname in self.orphanes:
            id = os.path.splitext(fname)[0]
            res = asyncio.run(self.joplin.delete_resources(id))
            print('deleting: {} {}'.format(fname, res))    
    
    def sql_align_db(self):
        cmd = 'VACUUM;'    
        self.cursor.execute(cmd)
        print('database has been aligned...')
    
    
    def sql_get_notes(self, verbose=False):
        cmd = 'SELECT id, title FROM notes'
        
        if verbose: print('\nnotes:')
        notes = []
        for l in self.cursor.execute(cmd):
            id, title = l[0], l[1]
            notes.append(id)
            if verbose:
                print(id, '\t', title)
        if verbose and notes == []:
            print('no notes found ...')
        return notes
    
    def sql_get_folders(self, verbose=False):
       
        cmd = ' SELECT id FROM folders'
        
        if verbose: print('\nfolders:')
        folders = []
        for l in self.cursor.execute(cmd): 
            id = l[0]
            folders.append(id)
            if verbose: print(id)
        return folders
    
    def sql_get_tags(self, verbose=False):
       
        cmd = ' SELECT id, title FROM tags'
        
        if verbose: print('\ntags:')
        tags = []
        for l in self.cursor.execute(cmd): 
            id, title = (l)
            tags.append(id)
            if verbose: print(id, title)
        return tags
    
    
    def sql_get_tagtitle(self, id):
        title = ''
        cmd = ' SELECT id, title FROM tags WHERE id = "{}"'.format(id)
        
        for l in self.cursor.execute(cmd):
            id, title = (l)
        return title
    
    
    def sql_get_resource_title(self, id):
        size, title = '',''
        
        cmd = 'SELECT id, title FROM resources WHERE id = "{}"'.format(id)
        for l in self.cursor.execute(cmd):
            id, title = (l)
        return title
    
    def sql_get_resources(self, verbose=False):
        cmd = 'SELECT id, file_extension from resources ORDER BY id'
        
        if verbose: print('\nresources in sql database:')
        resources = []
        for l in self.cursor.execute(cmd):
            id, ext = l[0], l[1]
            fname = id + '.' + ext
            resources.append(fname)
            if verbose:
                print(fname)
        return resources        
    
        
    def sql_get_foldertitle(self, id):
        title = ''
        
        cmd = 'SELECT id, title FROM folders WHERE id = "{}"'.format(id)
        for l in self.cursor.execute(cmd):
            id, title = (l)
            
        return title    
        
    
    def sql_get_notetitle(self, id):
        title = ''
        
        cmd = 'SELECT id, title FROM notes WHERE id = "{}"'.format(id)
        for l in self.cursor.execute(cmd):
            id, title = (l)
        return title
    
    
                
    def check_dropbox(self, do_delete=False): # extract filetype fom md files
        ''' checks if md files exist in database and resource dir'''

        def fmtprint(str1='',str2='',str3=''): # formatted output to 80 width console
            print('{:<15.13}{:<35.33}{:.28}'.format(str1,str2,str3))

        def get_type(fname):
            typ = None
            with open(fname, encoding='utf-8') as f:
                while True:
                    l = f.readline()
                    if l == '':
                        break
                    if l.startswith('type_:'):
                        typ = int(l.lstrip('type_:'))
                        break
            return typ
    
    
        notes = self.sql_get_notes()
        folders = self.sql_get_folders()
        tags = self.sql_get_tags()
        notfound = 0
        
        print('\nchecking dropbox(if notes, folder, images exist in database / resourcedir):')
        print('---------------------------------------------------------------------------')
        n, special = 0, 0
        notecnt, foldercnt, imgcnt, tagcnt = 0,0,0,0
        
        for f in os.listdir(self.path_Dropbox):
            id, e = os.path.splitext(f)
            
            if e == '.md':
                n += 1
                typ = get_type(join(self.path_Dropbox,f))
                                    
                if typ == 1:
                    if id in notes:   
                        notecnt +=1
                        fmtprint('valid note', id, self.sql_get_notetitle(id))
                    else:            
                        fmtprint('unlinked note', id, self.sql_get_notetitle(id) )
                        notfound += 1
                
                elif  typ == 2:
                    if id in folders: 
                        foldercnt += 1
                        fmtprint('valid folder', id, self.sql_get_foldertitle(id) )
                    else:            
                        fmtprint('unlinked folder', id, self.sql_get_foldertitle(id) )
                        notfound += 1
                        
                elif typ == 4:
                    if self.sql_get_resource_title (id) != '':
                        imgcnt += 1
                        fmtprint('valid image', id, self.sql_get_resource_title(id) )
                    else:
                        fmtprint('unlinked image', id, self.sql_get_resource_title(id) )
                        notfound += 1
    
                elif typ == 5:
                    if id in tags:  
                        tagcnt += 1
                        fmtprint('valid tag', id, self.sql_get_tagtitle(id) )
                    else:            
                        fmtprint('unlinked tag', id, self.sql_get_tagtitle(id) )
                        notfound += 1
                        
                elif typ in (6,7,8,9,10,11,12,13,14):
                    n -= 1
                    special += 1
                    fmtprint('type_' + str(typ), id) 
                   
                else:
                    
                    fmtprint('# not valid #', id)
                    special += 1
                    notfound += 1
                    
                    if do_delete:
                        os.remove(os.path.join(self.path_Dropbox, f))
                        print('removed:         ', f)
                        notfound -= 1
                     
        n -= notfound
        print('\nnotes:    ', notecnt)
        print('folders:  ', foldercnt)
        print('images:   ', imgcnt)
        print('tags:     ', tagcnt)
        print('total:    ', n)
        print('\nnotfound: ', notfound)
        print('special:  ', special)
        
        if notfound == 0:
            print('\nfiles in dropbox seem to be OK ...')
        else:
            print('\nunlinked files in Dropbox ... please remove')
'''
# todo 
BaseModel.typeEnum_ = [['TYPE_NOTE', 1], 
                       ['TYPE_FOLDER', 2], 
                       ['TYPE_SETTING', 3], 
                       ['TYPE_RESOURCE', 4], 
                       ['TYPE_TAG', 5],
                       ['TYPE_NOTE_TAG', 6], 
                       ['TYPE_SEARCH', 7],
                       ['TYPE_ALARM', 8], 
                       ['TYPE_MASTER_KEY', 9], 
                       ['TYPE_ITEM_CHANGE', 10], 
                       ['TYPE_NOTE_RESOURCE', 11], 
                       ['TYPE_RESOURCE_LOCAL_STATE', 12], 
                       ['TYPE_REVISION', 13], 
                       ['TYPE_MIGRATION', 14]];
'''   



            

joplintool = JoplinHelper()

parser = argparse.ArgumentParser(description= 'joplintool by pat 0.9.1 (based upon work from foxmask and tessus)\n\n'
                                 '  - checks and removes orphaned files in local resourcedir and remote sync dir\n'
                                 '  - default is a dryrun, nothing will be deleted\n'
                                 '  - removal of orphanes ignores timestamps...\n\n'
                                 '  - use --force if you know what you are doing\n'
                                 '  - EXPORT A BACKUP BEFORE USE !\n',
                                 formatter_class=argparse.RawTextHelpFormatter)                  
parser.add_argument("-checkr","--checkresources", action="store_true", help="checks for orphanes files in resourcedir") 
parser.add_argument("-checkd","--checkdropbox", action="store_true", help="checks for orphanes files in dropboxdir") 
parser.add_argument("-force","--force", action="store_true", help="enables delete for checkorphanes and checkdropbox") 
parser.add_argument("-r","--recurse", action="store_true" ,help="recurses through folders and notes / shows tree") 
#parser.add_argument("-d","--debug", action="store_true", help='internal use')
parser.add_argument("-a","--align", action="store_true", help="deflate/pack db after data was deleted...")
parser.add_argument("-i","--info", action="store_true", help="shows how many notes, folders, imagerefs are stored in the db")
args = parser.parse_args()

if len(sys.argv)==1:    # print help if no arguments given (if needed..)
    parser.print_help()
    exit()

if args.checkresources:
    joplintool.check_resources(do_delete=args.force)
if args.checkdropbox:
    joplintool.check_dropbox(do_delete=args.force)
if args.recurse:
    joplintool.recurse_folders()
if args.align:
    joplintool.sql_align_db()
if args.info:
    joplintool.info()
#if args.debug:
#    print('0123456789'*8)





